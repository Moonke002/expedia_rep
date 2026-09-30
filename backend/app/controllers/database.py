"""SQLite controller for the seed, accounts, searches, and booking CRUD."""

import csv
import hashlib
import hmac
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from ..models import Booking, Hotel, StayResult, Traveler, Trip
from .pricing import quote


DATA_DIR = Path(__file__).resolve().parents[2]
DATABASE_FILE = DATA_DIR / "expedia.sqlite3"
LEGACY_BOOKINGS_FILE = DATA_DIR / "bookings.sqlite3"
DEMO_PASSWORD = "DemoPass123!"
SESSION_DAYS = 7
PASSWORD_ROUNDS = 200_000


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ROUNDS)
    return f"{salt.hex()}${digest.hex()}"


def password_matches(password: str, stored: str) -> bool:
    try:
        salt_hex, _digest = stored.split("$", 1)
        return hmac.compare_digest(password_hash(password, bytes.fromhex(salt_hex)), stored)
    except (ValueError, AttributeError):
        return False


class StoreError(Exception):
    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


class DatabaseController:
    def __init__(
        self,
        db_path: Path = DATABASE_FILE,
        data_dir: Path = DATA_DIR,
        legacy_bookings_path: Path | None = LEGACY_BOOKINGS_FILE,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.db_path = db_path
        self.data_dir = data_dir
        self.legacy_bookings_path = legacy_bookings_path
        self.clock = clock
        self._ready = False

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self.db_path, timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            if not self._ready:
                self._initialize(connection)
            return connection
        except (OSError, sqlite3.DatabaseError, KeyError, ValueError, StoreError) as error:
            if "connection" in locals():
                connection.close()
            if isinstance(error, StoreError):
                raise
            raise StoreError(f"Travel data is unavailable: {error}") from error

    def _initialize(self, connection: sqlite3.Connection) -> None:
        # An immediate transaction makes concurrent first requests seed exactly once.
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("""CREATE TABLE IF NOT EXISTS hotels (
                hotel_id TEXT PRIMARY KEY, hotel_name TEXT NOT NULL, city TEXT NOT NULL,
                state TEXT NOT NULL, nightly_rate_usd INTEGER NOT NULL CHECK (nightly_rate_usd >= 0)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS trips (
                trip_id TEXT PRIMARY KEY, hotel_id TEXT NOT NULL REFERENCES hotels(hotel_id),
                trip_name TEXT NOT NULL, check_in TEXT NOT NULL, check_out TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY, display_name TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS bookings (
                booking_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
                trip_id TEXT NOT NULL REFERENCES trips(trip_id), booked_on TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
                source TEXT NOT NULL CHECK (source IN ('sample', 'created'))
            )""")
            if connection.execute("SELECT 1 FROM metadata WHERE key = 'seeded'").fetchone() is None:
                self._seed(connection)
                connection.execute("INSERT INTO metadata VALUES ('seeded', '1')")
            self._upgrade_accounts(connection)
            connection.execute("""CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
                expires_at TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS search_history (
                search_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                query TEXT NOT NULL, normalized_query TEXT NOT NULL,
                searched_at TEXT NOT NULL
            )""")
            connection.execute("""CREATE INDEX IF NOT EXISTS search_frequency
                ON search_history(user_id, normalized_query, searched_at)""")
            connection.commit()
            self._ready = True
        except (OSError, sqlite3.DatabaseError, KeyError, ValueError) as error:
            connection.rollback()
            raise StoreError(f"Travel data could not be initialized: {error}") from error

    def _csv_rows(self, name: str, columns: set[str]) -> list[dict[str, str]]:
        with (self.data_dir / name).open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            if not columns.issubset(reader.fieldnames or []):
                raise ValueError(f"{name} is missing required columns")
            return list(reader)

    def _seed(self, connection: sqlite3.Connection) -> None:
        hotels = self._csv_rows("hotels.csv", set(Hotel.model_fields))
        trips = self._csv_rows("trips.csv", set(Trip.model_fields))
        users = self._csv_rows("users.csv", set(Traveler.model_fields))
        bookings = self._csv_rows(
            "bookings.csv", {"booking_id", "user_id", "trip_id", "booked_on", "status"}
        )
        connection.executemany(
            "INSERT INTO hotels VALUES (:hotel_id, :hotel_name, :city, :state, :nightly_rate_usd)", hotels
        )
        connection.executemany(
            "INSERT INTO trips VALUES (:trip_id, :hotel_id, :trip_name, :check_in, :check_out)", trips
        )
        connection.executemany("INSERT INTO users (user_id, display_name) VALUES (:user_id, :display_name)", users)
        connection.executemany(
            """INSERT INTO bookings VALUES
               (:booking_id, :user_id, :trip_id, :booked_on, :status, 'sample')""", bookings
        )
        # Preserve changes made by the previous release without altering its old database.
        if self.legacy_bookings_path and self.legacy_bookings_path.exists():
            with closing(sqlite3.connect(self.legacy_bookings_path.as_uri() + "?mode=ro", uri=True)) as old:
                for booking in old.execute(
                    "SELECT booking_id, user_id, trip_id, booked_on, status, source FROM bookings"
                ):
                    connection.execute(
                        """INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?)
                           ON CONFLICT(booking_id) DO UPDATE SET
                           user_id=excluded.user_id, trip_id=excluded.trip_id,
                           booked_on=excluded.booked_on, status=excluded.status,
                           source=excluded.source""",
                        booking,
                    )

    def _upgrade_accounts(self, connection: sqlite3.Connection) -> None:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
        if "username" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "password_hash" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        for row in connection.execute("SELECT user_id FROM users WHERE username IS NULL"):
            suffix = row["user_id"][1:]
            username = f"demo{int(suffix)}" if suffix.isdigit() else f"demo-{row['user_id'].lower()}"
            connection.execute(
                "UPDATE users SET username = ?, password_hash = ? WHERE user_id = ?",
                (username, password_hash(DEMO_PASSWORD), row["user_id"]),
            )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS unique_username ON users(username COLLATE NOCASE)"
        )

    @staticmethod
    def _hotel(row: sqlite3.Row) -> Hotel:
        return Hotel(
            hotel_id=row["hotel_id"], hotel_name=row["hotel_name"], city=row["city"],
            state=row["state"], nightly_rate_usd=row["nightly_rate_usd"],
        )

    @staticmethod
    def _trip(row: sqlite3.Row) -> Trip:
        return Trip(
            trip_id=row["trip_id"], hotel_id=row["stay_hotel_id"], trip_name=row["trip_name"],
            check_in=row["check_in"], check_out=row["check_out"],
        )

    _STAY_COLUMNS = """h.hotel_id, h.hotel_name, h.city, h.state, h.nightly_rate_usd,
        t.trip_id, t.hotel_id AS stay_hotel_id, t.trip_name, t.check_in, t.check_out"""

    def search_stays(self, hotel_name: str, matching_searches_today: int = 0) -> list[dict]:
        with closing(self._connect()) as connection:
            # Treat % and _ as literal search characters rather than SQL wildcards.
            escaped = hotel_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            rows = connection.execute(
                f"""SELECT {self._STAY_COLUMNS} FROM hotels h
                    JOIN trips t ON t.hotel_id = h.hotel_id
                    WHERE h.hotel_name LIKE ? ESCAPE '\\' COLLATE NOCASE
                    ORDER BY h.hotel_id, t.trip_id""",
                (f"%{escaped}%",),
            ).fetchall()
            return [
                StayResult(
                    hotel=self._hotel(row), stay=self._trip(row),
                    pricing=quote(row["nightly_rate_usd"], matching_searches_today),
                ).model_dump()
                for row in rows
            ]

    def record_search(self, user_id: str, query: str) -> int:
        normalized = query.strip().casefold()
        now = self.clock().astimezone(timezone.utc)
        start = f"{now.date().isoformat()}T00:00:00+00:00"
        end = f"{(now.date() + timedelta(days=1)).isoformat()}T00:00:00+00:00"
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            with connection:
                connection.execute(
                    "INSERT INTO search_history (user_id, query, normalized_query, searched_at) VALUES (?, ?, ?, ?)",
                    (user_id, query, normalized, now.isoformat()),
                )
                if not normalized:
                    return 0
                return connection.execute(
                    """SELECT count(*) FROM search_history WHERE user_id = ?
                       AND normalized_query = ? AND searched_at >= ? AND searched_at < ?""",
                    (user_id, normalized, start, end),
                ).fetchone()[0]

    @staticmethod
    def _public_user(row: sqlite3.Row) -> dict:
        return {"user_id": row["user_id"], "display_name": row["display_name"], "username": row["username"]}

    def register_account(self, username: str, password: str, display_name: str = "") -> dict:
        username = username.strip().lower()
        if not re.fullmatch(r"[a-z0-9_.-]{3,30}", username):
            raise StoreError("Username must be 3–30 letters, numbers, dots, dashes, or underscores.", 422)
        if len(password) < 8:
            raise StoreError("Password must be at least 8 characters.", 422)
        display_name = display_name.strip() or username
        if len(display_name) > 80:
            raise StoreError("Display name must be 80 characters or fewer.", 422)
        with closing(self._connect()) as connection, connection:
            if connection.execute(
                "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username,)
            ).fetchone():
                raise StoreError("Username is already taken.", 409)
            for _ in range(3):
                user_id = f"U{uuid4().hex[:16].upper()}"
                try:
                    connection.execute(
                        "INSERT INTO users (user_id, display_name, username, password_hash) VALUES (?, ?, ?, ?)",
                        (user_id, display_name, username, password_hash(password)),
                    )
                    return {"user_id": user_id, "display_name": display_name, "username": username}
                except sqlite3.IntegrityError as error:
                    if "users.user_id" in str(error):
                        continue
                    if "username" in str(error).lower():
                        raise StoreError("Username is already taken.", 409) from error
                    raise StoreError("Account could not be created.") from error
            raise StoreError("Could not assign a unique user ID.")

    def login(self, username: str, password: str) -> tuple[dict, str]:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT user_id, display_name, username, password_hash FROM users WHERE username = ? COLLATE NOCASE",
                (username.strip(),),
            ).fetchone()
            if row is None or not password_matches(password, row["password_hash"]):
                raise StoreError("Incorrect username or password.", 401)
            token = secrets.token_urlsafe(32)
            expires = (self.clock().astimezone(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
            connection.execute(
                "INSERT INTO sessions VALUES (?, ?, ?)",
                (hashlib.sha256(token.encode()).hexdigest(), row["user_id"], expires),
            )
            return self._public_user(row), token

    def current_user(self, token: str | None) -> dict | None:
        if not token:
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT u.user_id, u.display_name, u.username FROM sessions s
                   JOIN users u ON u.user_id = s.user_id
                   WHERE s.token_hash = ? AND s.expires_at > ?""",
                (hashlib.sha256(token.encode()).hexdigest(), self.clock().astimezone(timezone.utc).isoformat()),
            ).fetchone()
            return self._public_user(row) if row else None

    def logout(self, token: str | None) -> None:
        if token:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    "DELETE FROM sessions WHERE token_hash = ?", (hashlib.sha256(token.encode()).hexdigest(),)
                )

    def list_users(self) -> list[dict]:
        with closing(self._connect()) as connection:
            return [
                Traveler(**dict(row)).model_dump()
                for row in connection.execute("SELECT user_id, display_name FROM users ORDER BY user_id")
            ]

    @staticmethod
    def _require(connection: sqlite3.Connection, table: str, id_column: str, value: str, label: str) -> None:
        # Table/column names are constants controlled by this module, never user input.
        if connection.execute(f"SELECT 1 FROM {table} WHERE {id_column} = ?", (value,)).fetchone() is None:
            raise StoreError(f"{label} not found.", 404)

    def _booking(self, connection: sqlite3.Connection, booking_id: str) -> dict:
        row = connection.execute(
            f"""SELECT b.booking_id, b.user_id, b.trip_id AS booking_trip_id,
                b.booked_on, b.status, b.source, {self._STAY_COLUMNS}
                FROM bookings b JOIN trips t ON t.trip_id = b.trip_id
                JOIN hotels h ON h.hotel_id = t.hotel_id WHERE b.booking_id = ?""",
            (booking_id,),
        ).fetchone()
        if row is None:
            raise StoreError("Booking not found.", 404)
        return Booking(
            booking_id=row["booking_id"], user_id=row["user_id"],
            trip_id=row["booking_trip_id"], booked_on=row["booked_on"],
            status=row["status"], source=row["source"],
            stay=self._trip(row), hotel=self._hotel(row),
        ).model_dump()

    def list_bookings(self, user_id: str) -> list[dict]:
        with closing(self._connect()) as connection:
            self._require(connection, "users", "user_id", user_id, "Traveler")
            ids = connection.execute(
                "SELECT booking_id FROM bookings WHERE user_id = ? ORDER BY booked_on DESC, booking_id DESC",
                (user_id,),
            ).fetchall()
            return [self._booking(connection, row["booking_id"]) for row in ids]

    def create_booking(self, user_id: str, trip_id: str) -> dict:
        with closing(self._connect()) as connection, connection:
            self._require(connection, "users", "user_id", user_id, "Traveler")
            self._require(connection, "trips", "trip_id", trip_id, "Stay")
            # UUID-based IDs never consume or renumber the supplied B001... IDs.
            for _ in range(3):
                booking_id = f"B{uuid4().hex[:16].upper()}"
                try:
                    connection.execute(
                        "INSERT INTO bookings VALUES (?, ?, ?, ?, 'confirmed', 'created')",
                        (booking_id, user_id, trip_id, self.clock().astimezone(timezone.utc).date().isoformat()),
                    )
                    return self._booking(connection, booking_id)
                except sqlite3.IntegrityError as error:
                    if "bookings.booking_id" not in str(error):
                        raise StoreError(f"Booking could not be saved: {error}") from error
            raise StoreError("Could not assign a unique booking ID.")

    def cancel_booking(self, booking_id: str, status: str, user_id: str) -> dict:
        with closing(self._connect()) as connection, connection:
            booking = self._booking(connection, booking_id)
            if booking["user_id"] != user_id:
                raise StoreError("Booking not found.", 404)
            if status != "cancelled":
                raise StoreError("Only cancellation is supported.", 422)
            connection.execute(
                "UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?", (booking_id,)
            )
            return self._booking(connection, booking_id)

    def delete_test_booking(self, booking_id: str, user_id: str) -> None:
        with closing(self._connect()) as connection, connection:
            booking = self._booking(connection, booking_id)
            if booking["user_id"] != user_id:
                raise StoreError("Booking not found.", 404)
            if booking["source"] != "created":
                raise StoreError("Supplied sample bookings cannot be deleted.", 403)
            connection.execute("DELETE FROM bookings WHERE booking_id = ?", (booking_id,))
