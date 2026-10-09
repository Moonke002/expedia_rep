import httpx
import pytest

from app.controllers import geocoding
from app.controllers.geocoding import (
    GeoapifyAuthenticationError,
    GeoapifyProviderError,
    lookup_postcode,
    lookup_postcode_with_hotels,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_lookup_postcode_returns_matching_location(monkeypatch):
    captured = {}
    monkeypatch.setattr(geocoding, "get_geoapify_api_key", lambda: "demo-key")

    def fake_get(url, *, params, timeout):
        captured.update(url=url, params=params, timeout=timeout)
        return FakeResponse({
            "results": [{
                "postcode": "16802", "country_code": "us", "lat": 40.7984,
                "lon": -77.8599, "city": "State College",
            }]
        })

    monkeypatch.setattr(geocoding.httpx, "get", fake_get)

    assert lookup_postcode("16802") == {
        "postcode": "16802",
        "country_code": "us",
        "latitude": 40.7984,
        "longitude": -77.8599,
        "locality": "State College",
    }
    assert captured["url"] == geocoding.GEOCODING_URL
    assert captured["params"] == {
        "text": "16802", "type": "postcode", "filter": "countrycode:us",
        "format": "json", "apiKey": "demo-key",
    }
    assert captured["timeout"] == geocoding.REQUEST_TIMEOUT_SECONDS


def test_lookup_postcode_returns_none_for_mismatched_location(monkeypatch):
    monkeypatch.setattr(geocoding, "get_geoapify_api_key", lambda: "demo-key")
    monkeypatch.setattr(
        geocoding.httpx,
        "get",
        lambda *args, **kwargs: FakeResponse({
            "results": [{"postcode": "16801", "country_code": "us", "lat": 40, "lon": -77}]
        }),
    )

    assert lookup_postcode("16802") is None


def test_lookup_postcode_distinguishes_provider_failure(monkeypatch):
    monkeypatch.setattr(geocoding, "get_geoapify_api_key", lambda: "demo-key")

    def failed_get(*args, **kwargs):
        raise httpx.TimeoutException("provider timed out")

    monkeypatch.setattr(geocoding.httpx, "get", failed_get)

    with pytest.raises(GeoapifyProviderError, match="^Geoapify lookup failed\\.$") as error:
        lookup_postcode("16802")
    assert "demo-key" not in str(error.value)


def test_lookup_postcode_identifies_rejected_api_key_without_echoing_it(monkeypatch):
    monkeypatch.setattr(geocoding, "get_geoapify_api_key", lambda: "secret-demo-key")
    request = httpx.Request("GET", geocoding.GEOCODING_URL)
    response = httpx.Response(401, request=request, json={"error": "Unauthorized"})

    def rejected_get(*args, **kwargs):
        raise httpx.HTTPStatusError("Unauthorized", request=request, response=response)

    monkeypatch.setattr(geocoding.httpx, "get", rejected_get)

    with pytest.raises(GeoapifyAuthenticationError, match="^Geoapify rejected the configured API key\.$") as error:
        lookup_postcode("19014")
    assert "secret-demo-key" not in str(error.value)


def test_lookup_postcode_with_hotels_uses_verified_point_and_radius(monkeypatch):
    calls = []
    monkeypatch.setattr(geocoding, "get_geoapify_api_key", lambda: "demo-key")

    def fake_get(url, *, params, timeout):
        calls.append((url, params))
        if url == geocoding.GEOCODING_URL:
            return FakeResponse({"results": [{"postcode": "01234", "country_code": "us", "lat": 40.0, "lon": -77.0}]})
        return FakeResponse({"features": [
            {"properties": {"place_id": "provider:Exact-ID", "name": "Near Hotel", "city": "Neartown"}, "geometry": {"coordinates": [-77.001, 40.001]}},
            {"properties": {"name": "Far Hotel"}, "geometry": {"coordinates": [-77.1, 40.1]}},
        ]})

    monkeypatch.setattr(geocoding.httpx, "get", fake_get)
    result = lookup_postcode_with_hotels("01234")

    assert result["postcode"] == "01234"
    assert [hotel["name"] for hotel in result["hotels"]] == ["Near Hotel"]
    assert result["hotels"][0]["provider_id"] == "provider:Exact-ID"
    assert calls[1][0] == geocoding.PLACES_URL
    assert calls[1][1]["filter"] == "circle:-77.0,40.0,5000"


def test_lookup_postcode_with_hotels_does_not_search_when_unresolved(monkeypatch):
    urls = []
    monkeypatch.setattr(geocoding, "get_geoapify_api_key", lambda: "demo-key")
    monkeypatch.setattr(geocoding.httpx, "get", lambda url, **kwargs: (urls.append(url) or FakeResponse({"results": []})))

    assert lookup_postcode_with_hotels("01234") is None
    assert urls == [geocoding.GEOCODING_URL]
