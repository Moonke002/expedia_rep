from fastapi.testclient import TestClient

from app import main


def test_search_preserves_part_one_behavior() -> None:
    client = TestClient(main.app)
    trail = client.get("/api/hotels/search", params={"hotel_name": "Trail"})
    assert trail.status_code == 200
    assert {item["hotel"]["hotel_name"] for item in trail.json()["results"]} == {
        "Valley Trail Inn"
    }

    inns = client.get("/api/hotels/search", params={"hotel_name": "Inn"})
    assert {item["hotel"]["hotel_name"] for item in inns.json()["results"]} == {
        "Liberty Lane Inn", "Maple Square Inn", "Valley Trail Inn"
    }
    missing = client.get("/api/hotels/search", params={"hotel_name": "No Such Hotel"})
    assert missing.status_code == 200
    assert missing.json()["results"] == []


def test_booking_create_read_cancel_and_delete(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "BOOKINGS_DB", tmp_path / "test-bookings.sqlite3")
    client = TestClient(main.app)

    history = client.get("/api/bookings", params={"user_id": "U001"})
    assert history.status_code == 200
    assert {booking["booking_id"] for booking in history.json()["bookings"]} == {
        "B001", "B002"
    }

    created = client.post("/api/bookings", json={"user_id": "U001", "trip_id": "T009"})
    assert created.status_code == 201
    booking = created.json()
    assert booking["status"] == "confirmed"
    assert booking["hotel"]["hotel_id"] == booking["stay"]["hotel_id"] == "H001"
    booking_id = booking["booking_id"]

    history = client.get("/api/bookings", params={"user_id": "U001"})
    assert booking_id in {item["booking_id"] for item in history.json()["bookings"]}

    cancelled = client.patch(f"/api/bookings/{booking_id}", json={"status": "cancelled"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    retained = client.get("/api/bookings", params={"user_id": "U001"})
    assert next(item for item in retained.json()["bookings"] if item["booking_id"] == booking_id)[
        "status"
    ] == "cancelled"

    assert client.delete(f"/api/bookings/{booking_id}").status_code == 204
    final_history = client.get("/api/bookings", params={"user_id": "U001"})
    assert booking_id not in {item["booking_id"] for item in final_history.json()["bookings"]}
    assert client.delete("/api/bookings/B001").status_code == 403


def test_booking_rejects_unknown_references(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "BOOKINGS_DB", tmp_path / "test-bookings.sqlite3")
    client = TestClient(main.app)
    assert client.post("/api/bookings", json={"user_id": "missing", "trip_id": "T009"}).status_code == 404
    assert client.post("/api/bookings", json={"user_id": "U001", "trip_id": "missing"}).status_code == 404
