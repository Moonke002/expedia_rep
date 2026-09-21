import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import main
from app.controllers.database import DEMO_PASSWORD, DatabaseController


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        main, "controller", DatabaseController(db_path=tmp_path / "expedia.sqlite3", legacy_bookings_path=None)
    )
    return TestClient(main.app)


def login(client, username="demo1", password=DEMO_PASSWORD):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_seeded_relationships_and_search(client, tmp_path):
    trail = client.get("/api/hotels/search", params={"hotel_name": "Trail"})
    assert trail.status_code == 200
    assert {item["hotel"]["hotel_name"] for item in trail.json()["results"]} == {"Valley Trail Inn"}
    assert trail.json()["results"][0]["pricing"]["displayed_nightly_rate_usd"] == 100
    inns = client.get("/api/hotels/search", params={"hotel_name": "Inn"})
    assert {item["hotel"]["hotel_name"] for item in inns.json()["results"]} == {
        "Liberty Lane Inn", "Maple Square Inn", "Valley Trail Inn"
    }
    assert client.get("/api/hotels/search", params={"hotel_name": "No Such Hotel"}).json()["results"] == []
    assert client.get("/api/hotels/search", params={"hotel_name": "%"}).json()["results"] == []
    assert len(client.get("/api/hotels/search").json()["results"]) == 12
    assert len(client.get("/api/users").json()["users"]) == 6
    with sqlite3.connect(tmp_path / "expedia.sqlite3") as db:
        assert [db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("hotels", "trips", "users", "bookings")] == [8, 12, 6, 6]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        db.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO trips VALUES ('T999', 'missing', 'Invalid', '2026-11-01', '2026-11-02')")


def test_account_create_login_logout_and_restart(client, tmp_path, monkeypatch):
    assert client.get("/api/auth/me").json()["user"] is None
    assert client.get("/api/bookings").status_code == 401
    assert login(client, "demo1", "wrong-password").status_code == 401
    assert client.get("/api/auth/me").json()["user"] is None
    created = client.post("/api/auth/register", json={
        "username": " NewGuest ", "password": "ExamplePass123!", "display_name": "New Guest"
    })
    assert created.status_code == 201
    user = created.json()["user"]
    assert user["username"] == "newguest" and user["user_id"] not in {f"U{i:03}" for i in range(1, 7)}
    assert client.post("/api/auth/register", json={
        "username": "NEWGUEST", "password": "ExamplePass123!"
    }).status_code == 409
    assert client.post("/api/auth/register", json={"username": "x", "password": "short"}).status_code == 422
    assert login(client, "newguest", "ExamplePass123!").status_code == 200
    assert client.get("/api/auth/me").json()["user"]["user_id"] == user["user_id"]
    with sqlite3.connect(tmp_path / "expedia.sqlite3") as db:
        stored = db.execute("SELECT password_hash FROM users WHERE user_id = ?", (user["user_id"],)).fetchone()[0]
        assert "ExamplePass123!" not in stored
        assert db.execute("SELECT count(*) FROM bookings WHERE booking_id = 'B001'").fetchone()[0] == 1
    monkeypatch.setattr(main, "controller", DatabaseController(
        db_path=tmp_path / "expedia.sqlite3", legacy_bookings_path=None
    ))
    assert client.get("/api/auth/me").json()["user"]["user_id"] == user["user_id"]
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").json()["user"] is None
    assert client.get("/api/bookings").status_code == 401


def test_booking_crud_is_bound_to_signed_in_user(client, tmp_path, monkeypatch):
    assert login(client).status_code == 200
    history = client.get("/api/bookings").json()["bookings"]
    assert {booking["booking_id"] for booking in history} == {"B001", "B002"}
    assert client.post("/api/bookings", json={"trip_id": "T009", "user_id": "U002"}).status_code == 422
    created = client.post("/api/bookings", json={"trip_id": "T009"})
    assert created.status_code == 201
    booking = created.json()
    assert booking["user_id"] == "U001" and booking["status"] == "confirmed"
    assert booking["hotel"]["hotel_id"] == booking["stay"]["hotel_id"] == "H001"
    booking_id = booking["booking_id"]
    second = client.post("/api/bookings", json={"trip_id": "T009"}).json()
    assert second["booking_id"] != booking_id
    monkeypatch.setattr(main, "controller", DatabaseController(
        db_path=tmp_path / "expedia.sqlite3", legacy_bookings_path=None
    ))
    assert booking_id in {item["booking_id"] for item in client.get("/api/bookings").json()["bookings"]}
    assert login(client, "demo2").status_code == 200
    assert booking_id not in {item["booking_id"] for item in client.get("/api/bookings").json()["bookings"]}
    assert client.patch(f"/api/bookings/{booking_id}", json={"status": "cancelled"}).status_code == 404
    assert client.delete(f"/api/bookings/{booking_id}").status_code == 404
    assert login(client).status_code == 200
    cancelled = client.patch(f"/api/bookings/{booking_id}", json={"status": "cancelled"})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert next(b for b in client.get("/api/bookings").json()["bookings"] if b["booking_id"] == booking_id)["status"] == "cancelled"
    assert client.delete(f"/api/bookings/{booking_id}").status_code == 204
    assert booking_id not in {item["booking_id"] for item in client.get("/api/bookings").json()["bookings"]}
    assert client.delete("/api/bookings/B001").status_code == 403


def test_search_frequency_is_per_user_query_and_utc_day(tmp_path, monkeypatch):
    now = [datetime(2026, 9, 21, 23, 59, tzinfo=timezone.utc)]
    db_path = tmp_path / "expedia.sqlite3"
    monkeypatch.setattr(main, "controller", DatabaseController(
        db_path=db_path, legacy_bookings_path=None, clock=lambda: now[0]
    ))
    a = TestClient(main.app)
    b = TestClient(main.app)
    assert login(a).status_code == 200
    for count, query in enumerate(("Trail", " trail ", "TRAIL", "tRaIl", "Trail"), start=1):
        payload = a.get("/api/hotels/search", params={"hotel_name": query}).json()
        result = payload["results"][0]
        assert payload["matching_searches_today"] == count
        assert result["pricing"]["displayed_nightly_rate_usd"] == (100 if count < 4 else 120)
        assert result["pricing"]["surge_applied"] is (count >= 4)
    assert a.get("/api/hotels/search", params={"hotel_name": "Valley Trail"}).json()["results"][0]["pricing"]["displayed_nightly_rate_usd"] == 100
    assert login(b, "demo2").status_code == 200
    assert b.get("/api/hotels/search", params={"hotel_name": "Trail"}).json()["results"][0]["pricing"]["displayed_nightly_rate_usd"] == 100
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT nightly_rate_usd FROM hotels WHERE hotel_id = 'H008'").fetchone()[0] == 100
        assert db.execute("SELECT count(*) FROM search_history").fetchone()[0] == 7
    now[0] += timedelta(minutes=2)
    monkeypatch.setattr(main, "controller", DatabaseController(
        db_path=db_path, legacy_bookings_path=None, clock=lambda: now[0]
    ))
    new_day = a.get("/api/hotels/search", params={"hotel_name": "Trail"}).json()
    assert new_day["matching_searches_today"] == 1
    assert new_day["results"][0]["pricing"]["displayed_nightly_rate_usd"] == 100


def test_invalid_references_and_sqlite_only_after_seed(client, tmp_path, monkeypatch):
    assert login(client).status_code == 200
    assert client.post("/api/bookings", json={"trip_id": "missing"}).status_code == 404
    assert client.patch("/api/bookings/B001", json={"status": "pending"}).status_code == 422
    assert client.delete("/api/bookings/missing").status_code == 404
    with sqlite3.connect(tmp_path / "expedia.sqlite3") as db:
        db.execute("INSERT INTO hotels VALUES ('H009', 'New Harbor Hotel', 'Boston', 'MA', 99)")
        db.execute("INSERT INTO trips VALUES ('T013', 'H009', 'New Stay', '2026-11-01', '2026-11-03')")
    fresh = DatabaseController(db_path=tmp_path / "expedia.sqlite3", legacy_bookings_path=None)
    monkeypatch.setattr(fresh, "_csv_rows", lambda *_: (_ for _ in ()).throw(AssertionError("CSV read after seed")))
    monkeypatch.setattr(main, "controller", fresh)
    found = client.get("/api/hotels/search", params={"hotel_name": "New Harbor"}).json()["results"]
    assert found[0]["stay"]["trip_id"] == "T013"
    assert found[0]["pricing"]["base_nightly_rate_usd"] == 99
    assert client.post("/api/bookings", json={"trip_id": "T013"}).status_code == 201


def test_legacy_bookings_migrate_without_changing_old_file(tmp_path, monkeypatch):
    old_path = tmp_path / "bookings.sqlite3"
    with sqlite3.connect(old_path) as old:
        old.execute("""CREATE TABLE bookings (
            booking_id TEXT PRIMARY KEY, user_id TEXT, trip_id TEXT,
            booked_on TEXT, status TEXT, source TEXT)""")
        old.execute("INSERT INTO bookings VALUES ('B001', 'U001', 'T001', '2026-09-01', 'cancelled', 'sample')")
        old.execute("INSERT INTO bookings VALUES ('BNEW', 'U001', 'T009', '2026-09-21', 'confirmed', 'created')")
    monkeypatch.setattr(main, "controller", DatabaseController(
        db_path=tmp_path / "expedia.sqlite3", legacy_bookings_path=old_path
    ))
    client = TestClient(main.app)
    assert login(client).status_code == 200
    history = client.get("/api/bookings").json()["bookings"]
    assert {b["booking_id"] for b in history} == {"B001", "B002", "BNEW"}
    assert next(b for b in history if b["booking_id"] == "B001")["status"] == "cancelled"
    with sqlite3.connect(old_path) as old:
        assert old.execute("SELECT count(*) FROM bookings").fetchone()[0] == 2
