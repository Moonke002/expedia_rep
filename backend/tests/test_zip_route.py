import pytest
from fastapi.testclient import TestClient

from app import main
from app.controllers.geocoding import (
    GeoapifyAuthenticationError,
    GeoapifyConfigurationError,
    GeoapifyProviderError,
)


def test_zip_location_route_returns_controller_location(monkeypatch):
    location = {
        "postcode": "16802",
        "country_code": "us",
        "latitude": 40.7984,
        "longitude": -77.8599,
        "locality": "State College",
    }
    requested = []
    monkeypatch.setattr(main, "lookup_postcode_with_hotels", lambda postcode: requested.append(postcode) or location)

    response = TestClient(main.app).get("/api/demo/zip-location?postcode=90210")

    assert response.status_code == 200
    assert response.json() == location
    assert requested == ["90210"]


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (GeoapifyConfigurationError("ignored"), 503, "ZIP lookup is not configured."),
        (
            GeoapifyAuthenticationError("ignored"),
            503,
            "Geoapify rejected its API key. Update GEOAPIFY_API_KEY in the project-root .env file, then restart FastAPI.",
        ),
        (GeoapifyProviderError("ignored"), 502, "ZIP lookup provider failed."),
    ],
)
def test_zip_location_route_maps_provider_errors(monkeypatch, error, status_code, detail):
    monkeypatch.setattr(main, "lookup_postcode_with_hotels", lambda postcode: (_ for _ in ()).throw(error))

    response = TestClient(main.app).get("/api/demo/zip-location")

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


def test_zip_location_route_maps_unresolved_zip(monkeypatch):
    monkeypatch.setattr(main, "lookup_postcode_with_hotels", lambda postcode: None)

    response = TestClient(main.app).get("/api/demo/zip-location")

    assert response.status_code == 404
    assert response.json() == {"detail": "ZIP code could not be resolved."}


def test_zip_location_route_rejects_non_five_digit_zip(monkeypatch):
    called = []
    monkeypatch.setattr(main, "lookup_postcode_with_hotels", lambda postcode: called.append(postcode))

    response = TestClient(main.app).get("/api/demo/zip-location?postcode=1234")

    assert response.status_code == 422
    assert called == []
