import csv
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(
    title="Expedia Rep API",
    description="Backend API for the Expedia Rep project.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parents[1]
HOTELS_FILE = DATA_DIR / "hotels.csv"
TRIPS_FILE = DATA_DIR / "trips.csv"
USERS_FILE = DATA_DIR / "users.csv"
BOOKINGS_FILE = DATA_DIR / "bookings.csv"
BOOKINGS_DB = DATA_DIR / "bookings.sqlite3"
HOTEL_NAME_COLUMNS = ("hotel_name", "name", "hotel")


class BookingCreate(BaseModel):
    user_id: str
    trip_id: str


class BookingStatusUpdate(BaseModel):
    status: str


def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"{label} data is missing. Add {path.name} to "
                f"{DATA_DIR} before searching."
            ),
        )

    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        return list(csv.DictReader(csv_file))


def _require_hotel_id(records: list[dict[str, str]], label: str) -> None:
    if records and "hotel_id" not in records[0]:
        raise HTTPException(
            status_code=500,
            detail=f"{label} data must contain a hotel_id column.",
        )


def _hotel_name(hotel: dict[str, str]) -> str:
    for column in HOTEL_NAME_COLUMNS:
        if hotel.get(column):
            return hotel[column]
    return hotel.get("hotel_id", "")


def _search_results(hotel_name: str) -> list[dict[str, Any]]:
    hotels = _read_csv(HOTELS_FILE, "Hotel")
    trips = _read_csv(TRIPS_FILE, "Trip")
    _require_hotel_id(hotels, "Hotels")
    _require_hotel_id(trips, "Trips")

    normalized_query = hotel_name.casefold()
    matching_hotels = [
        hotel
        for hotel in hotels
        if normalized_query in _hotel_name(hotel).casefold()
    ]

    trips_by_hotel: dict[str, list[dict[str, str]]] = defaultdict(list)
    for trip in trips:
        trips_by_hotel[trip.get("hotel_id", "")].append(trip)

    return [
        {"hotel": hotel, "stay": stay}
        for hotel in matching_hotels
        for stay in trips_by_hotel.get(hotel.get("hotel_id", ""), [])
    ]


def _booking_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(BOOKINGS_DB, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS bookings (
            booking_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            trip_id TEXT NOT NULL,
            booked_on TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
            source TEXT NOT NULL CHECK (source IN ('sample', 'created'))
        )"""
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    if connection.execute("SELECT 1 FROM metadata WHERE key = 'sample_seeded'").fetchone() is None:
        for booking in _read_csv(BOOKINGS_FILE, "Booking"):
            connection.execute(
                "INSERT OR IGNORE INTO bookings VALUES (?, ?, ?, ?, ?, 'sample')",
                (
                    booking["booking_id"], booking["user_id"], booking["trip_id"],
                    booking["booked_on"], booking["status"],
                ),
            )
        connection.execute(
            "INSERT INTO metadata (key, value) VALUES ('sample_seeded', '1')"
        )
    connection.commit()
    return connection


def _booking_details(booking: sqlite3.Row) -> dict[str, Any]:
    trips = {trip["trip_id"]: trip for trip in _read_csv(TRIPS_FILE, "Trip")}
    hotels = {hotel["hotel_id"]: hotel for hotel in _read_csv(HOTELS_FILE, "Hotel")}
    trip = trips.get(booking["trip_id"])
    hotel = hotels.get(trip["hotel_id"]) if trip else None
    return {**dict(booking), "stay": trip, "hotel": hotel}


def _find_booking(connection: sqlite3.Connection, booking_id: str) -> sqlite3.Row:
    booking = connection.execute(
        "SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)
    ).fetchone()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return booking

@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple liveness response."""
    return {"status": "ok"}


@app.get("/api/hotels/search")
def search_hotels(
    hotel_name: str = Query(default="", description="Hotel name to search for; blank lists all stays."),
) -> dict[str, Any]:
    """Return matching hotels joined to their available stays by hotel_id."""
    query = hotel_name.strip()
    results = _search_results(query)
    return {"query": query, "results": results}


@app.get("/api/users")
def list_users() -> dict[str, Any]:
    """List demo travelers available for simulated bookings."""
    return {"users": _read_csv(USERS_FILE, "Traveler")}


@app.get("/api/bookings")
def list_bookings(user_id: str = Query(description="Demo traveler ID.")) -> dict[str, Any]:
    """Return a traveler's persisted booking history."""
    if user_id not in {user["user_id"] for user in _read_csv(USERS_FILE, "Traveler")}:
        raise HTTPException(status_code=404, detail="Traveler not found.")
    with closing(_booking_connection()) as connection, connection:
        rows = connection.execute(
            "SELECT * FROM bookings WHERE user_id = ? ORDER BY booked_on DESC, booking_id DESC",
            (user_id,),
        ).fetchall()
        return {"bookings": [_booking_details(row) for row in rows]}


@app.post("/api/bookings", status_code=201)
def create_booking(request: BookingCreate) -> dict[str, Any]:
    """Create a simulated booking for one offered stay."""
    if request.user_id not in {user["user_id"] for user in _read_csv(USERS_FILE, "Traveler")}:
        raise HTTPException(status_code=404, detail="Traveler not found.")
    if request.trip_id not in {trip["trip_id"] for trip in _read_csv(TRIPS_FILE, "Trip")}:
        raise HTTPException(status_code=404, detail="Stay not found.")
    booking_id = f"B{uuid4().hex[:10].upper()}"
    with closing(_booking_connection()) as connection, connection:
        connection.execute(
            "INSERT INTO bookings VALUES (?, ?, ?, ?, 'confirmed', 'created')",
            (booking_id, request.user_id, request.trip_id, date.today().isoformat()),
        )
        return _booking_details(_find_booking(connection, booking_id))


@app.patch("/api/bookings/{booking_id}")
def update_booking_status(booking_id: str, request: BookingStatusUpdate) -> dict[str, Any]:
    """Cancel a booking while retaining it in history."""
    if request.status != "cancelled":
        raise HTTPException(status_code=422, detail="Only cancellation is supported.")
    with closing(_booking_connection()) as connection, connection:
        _find_booking(connection, booking_id)
        connection.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?", (booking_id,)
        )
        return _booking_details(_find_booking(connection, booking_id))


@app.delete("/api/bookings/{booking_id}", status_code=204)
def delete_test_booking(booking_id: str) -> Response:
    """Delete a booking created in the demo UI; preserve supplied sample records."""
    with closing(_booking_connection()) as connection, connection:
        booking = _find_booking(connection, booking_id)
        if booking["source"] != "created":
            raise HTTPException(status_code=403, detail="Supplied sample bookings cannot be deleted.")
        connection.execute("DELETE FROM bookings WHERE booking_id = ?", (booking_id,))
    return Response(status_code=204)
