import sqlite3

import pytest

from app.controllers.database import DatabaseController


def _initialized_controller(db_path):
    controller = DatabaseController(db_path=db_path, legacy_bookings_path=None)
    connection = controller._connect()
    connection.close()
    return controller


def test_saved_hotel_schema_defaults_constraints_and_repeatable_migration(tmp_path):
    db_path = tmp_path / "expedia.sqlite3"
    _initialized_controller(db_path)

    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA foreign_keys = ON")
        original_hotels = db.execute(
            "SELECT hotel_id, hotel_name, nightly_rate_usd FROM hotels ORDER BY hotel_id"
        ).fetchall()

        hotel_id = "geo-provider:AbC-001"
        db.execute(
            "INSERT INTO saved_hotels (hotel_id, latitude, longitude) VALUES (?, ?, ?)",
            (hotel_id, 40.0, -77.0),
        )
        db.execute(
            "INSERT INTO demo_hotel_nights (hotel_id, stay_date) VALUES (?, ?)",
            (hotel_id, "2026-10-02"),
        )
        assert db.execute(
            "SELECT nightly_rate_cents, rooms_available FROM demo_hotel_nights WHERE hotel_id = ?",
            (hotel_id,),
        ).fetchone() == (10000, 20)
        assert db.execute(
            "SELECT hotel_id, name, address, latitude, longitude FROM saved_hotels"
        ).fetchone() == (hotel_id, None, None, 40.0, -77.0)
        assert db.execute(
            "SELECT hotel_id FROM demo_hotel_nights WHERE stay_date = '2026-10-02'"
        ).fetchone() == (hotel_id,)

        invalid_inserts = (
            ("INSERT INTO saved_hotels VALUES ('bad-lat', 'Bad', NULL, 90.01, 0)", ()),
            ("INSERT INTO saved_hotels VALUES ('bad-lon', 'Bad', NULL, 0, -180.01)", ()),
            ("INSERT INTO demo_hotel_nights (hotel_id, stay_date) VALUES ('missing', '2026-10-02')", ()),
            ("INSERT INTO demo_hotel_nights (hotel_id, stay_date) VALUES (?, '2026-02-30')", (hotel_id,)),
            ("INSERT INTO demo_hotel_nights (hotel_id, stay_date, nightly_rate_cents) VALUES (?, '2026-10-03', -1)", (hotel_id,)),
            ("INSERT INTO demo_hotel_nights (hotel_id, stay_date, rooms_available) VALUES (?, '2026-10-03', -1)", (hotel_id,)),
        )
        for statement, parameters in invalid_inserts:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(statement, parameters)

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO saved_hotels (hotel_id, latitude, longitude) VALUES (?, 0, 0)",
                (hotel_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO demo_hotel_nights (hotel_id, stay_date) VALUES (?, ?)",
                (hotel_id, "2026-10-02"),
            )

        assert db.execute(
            "SELECT hotel_id, hotel_name, nightly_rate_usd FROM hotels ORDER BY hotel_id"
        ).fetchall() == original_hotels
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []

    # A second initialization leaves both the schema and saved rows intact.
    _initialized_controller(db_path)
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT hotel_id FROM saved_hotels").fetchall() == [("geo-provider:AbC-001",)]
        assert db.execute("SELECT count(*) FROM demo_hotel_nights").fetchone() == (1,)


def test_saved_hotel_migration_adds_tables_to_existing_database(tmp_path):
    db_path = tmp_path / "existing.sqlite3"
    _initialized_controller(db_path)
    with sqlite3.connect(db_path) as db:
        db.execute("INSERT INTO hotels VALUES ('H999', 'Existing Hotel', 'Town', 'TS', 123)")
        db.execute("INSERT INTO trips VALUES ('T999', 'H999', 'Existing Stay', '2026-10-01', '2026-10-02')")
        # Simulate a database created before these additive tables existed.
        db.execute("DROP TABLE demo_hotel_nights")
        db.execute("DROP TABLE saved_hotels")

    _initialized_controller(db_path)
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT hotel_name, nightly_rate_usd FROM hotels WHERE hotel_id = 'H999'").fetchone() == (
            "Existing Hotel", 123
        )
        assert db.execute("SELECT trip_id FROM trips WHERE trip_id = 'T999'").fetchone() == ("T999",)
        assert {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )} >= {"saved_hotels", "demo_hotel_nights"}
