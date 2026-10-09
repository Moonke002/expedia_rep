import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import main
from app.controllers.database import DatabaseController


@pytest.fixture
def saved_hotel_client(tmp_path, monkeypatch):
    db_path = tmp_path / "expedia.sqlite3"
    monkeypatch.setattr(
        main, "controller", DatabaseController(db_path=db_path, legacy_bookings_path=None)
    )
    return TestClient(main.app), db_path


def _hotel(provider_id="geo:Provider-ID-Exact"):
    return {
        "provider_id": provider_id,
        "name": "Demo Hotel",
        "address": "123 Sample Street",
        "latitude": 40.71,
        "longitude": -74.01,
    }


def _location(postcode="10001"):
    return {
        "postcode": postcode,
        "country_code": "us",
        "latitude": 40.75,
        "longitude": -73.99,
        "locality": "New York",
    }


def test_save_is_idempotent_preserves_rates_and_records_zip_context(tmp_path):
    db_path = tmp_path / "expedia.sqlite3"
    controller = DatabaseController(db_path=db_path, legacy_bookings_path=None)
    assert controller.save_api_hotel(_hotel(), _location()) == {
        "provider_id": "geo:Provider-ID-Exact", "postcode": "10001", "saved": True
    }
    with sqlite3.connect(db_path) as db:
        db.execute("""UPDATE demo_hotel_nights SET nightly_rate_cents=12500, rooms_available=3
                      WHERE hotel_id=? AND stay_date='2026-10-10'""", ("geo:Provider-ID-Exact",))

    changed_hotel = {**_hotel(), "name": "Updated provider name", "address": None}
    controller.save_api_hotel(changed_hotel, _location())
    controller.save_api_hotel(_hotel(), _location("10002"))

    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT hotel_id, name, address FROM saved_hotels").fetchall() == [
            ("geo:Provider-ID-Exact", "Demo Hotel", "123 Sample Street")
        ]
        assert db.execute("SELECT count(*) FROM demo_hotel_nights").fetchone() == (5,)
        assert db.execute("""SELECT nightly_rate_cents, rooms_available FROM demo_hotel_nights
                            WHERE hotel_id=? AND stay_date='2026-10-10'""", ("geo:Provider-ID-Exact",)).fetchone() == (12500, 3)
        assert db.execute("SELECT postcode FROM saved_hotel_zips ORDER BY postcode").fetchall() == [
            ("10001",), ("10002",)
        ]

    local = controller.get_saved_hotels_for_postcode("10001")
    assert local["latitude"] == 40.75 and local["locality"] == "New York"
    assert local["saved_provider_ids"] == ["geo:Provider-ID-Exact"]
    assert local["hotels"][0]["provider_id"] == "geo:Provider-ID-Exact"
    assert local["hotels"][0]["nightly_rates"][0] == {
        "stay_date": "2026-10-10", "nightly_rate_cents": 12500, "rooms_available": 3
    }
    assert controller.get_saved_hotels_for_postcode("99999")["hotels"] == []


def test_remove_deletes_one_hotel_and_its_children_only(tmp_path):
    db_path = tmp_path / "expedia.sqlite3"
    controller = DatabaseController(db_path=db_path, legacy_bookings_path=None)
    controller.save_api_hotel(_hotel("provider-one"), _location("10001"))
    controller.save_api_hotel(_hotel("provider-two"), _location("10001"))

    assert controller.remove_saved_hotel("provider-one") is True
    assert controller.remove_saved_hotel("provider-one") is False
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT hotel_id FROM saved_hotels").fetchall() == [("provider-two",)]
        assert db.execute("SELECT hotel_id FROM saved_hotel_zips").fetchall() == [("provider-two",)]
        assert db.execute("SELECT hotel_id, count(*) FROM demo_hotel_nights GROUP BY hotel_id").fetchall() == [
            ("provider-two", 5)
        ]
        db.execute("PRAGMA foreign_keys=ON")
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_saved_hotel_routes_save_list_and_remove(saved_hotel_client):
    client, _db_path = saved_hotel_client
    assert client.get("/api/saved-hotels", params={"postcode": "10001"}).json() == {
        "postcode": "10001", "hotels": [], "saved_provider_ids": []
    }

    response = client.post("/api/saved-hotels", json={"hotel": _hotel(), "location": _location()})
    assert response.status_code == 200
    assert response.json()["provider_id"] == "geo:Provider-ID-Exact"

    local = client.get("/api/saved-hotels", params={"postcode": "10001"})
    assert local.status_code == 200
    assert local.json()["hotels"][0]["nightly_rates"][0]["nightly_rate_cents"] == 10000
    assert len(local.json()["hotels"][0]["nightly_rates"]) == 5
    assert local.json()["saved_provider_ids"] == ["geo:Provider-ID-Exact"]

    assert client.delete("/api/saved-hotels/geo:Provider-ID-Exact").json() == {
        "provider_id": "geo:Provider-ID-Exact", "removed": True
    }
    assert client.delete("/api/saved-hotels/geo:Provider-ID-Exact").status_code == 404


def test_save_route_rejects_invalid_coordinates(saved_hotel_client):
    client, _db_path = saved_hotel_client
    invalid = {"hotel": {**_hotel(), "latitude": 90.1}, "location": _location()}
    assert client.post("/api/saved-hotels", json=invalid).status_code == 422
