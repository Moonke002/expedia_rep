"""Geoapify postcode lookup controller.

The controller returns a normalized location dictionary for a successful
match, ``None`` when Geoapify responds successfully without a matching U.S.
postcode, and ``GeoapifyProviderError`` when configuration, transport, or
provider response handling fails. It never returns the provider key or URL.
"""

import math
import re
from typing import TypedDict

import httpx

from ..config import get_geoapify_api_key


GEOCODING_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"
REQUEST_TIMEOUT_SECONDS = 5.0
HOTEL_RADIUS_METERS = 5000
POSTCODE_PATTERN = re.compile(r"^\d{5}$")


class LocationResponse(TypedDict, total=False):
    postcode: str
    country_code: str
    latitude: float
    longitude: float
    locality: str
    hotels: list["NearbyHotel"]


class NearbyHotel(TypedDict, total=False):
    provider_id: str
    name: str
    address: str
    locality: str
    distance_meters: int
    latitude: float
    longitude: float


class GeoapifyProviderError(RuntimeError):
    """Raised when a postcode lookup cannot be completed by Geoapify."""


class GeoapifyConfigurationError(GeoapifyProviderError):
    """Raised when the Geoapify key is not configured."""


class GeoapifyAuthenticationError(GeoapifyProviderError):
    """Raised when Geoapify rejects the configured key."""


def _coordinate(value: object, minimum: float, maximum: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(coordinate) or not minimum <= coordinate <= maximum:
        return None
    return coordinate


def _locality(result: dict) -> str | None:
    for field in ("locality", "city", "town", "village", "municipality"):
        value = result.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def lookup_postcode(postcode: str = "16802") -> LocationResponse | None:
    """Look up a U.S. postcode through Geoapify's forward geocoder.

    The request searches the postcode as ``text`` with ``type=postcode``, a
    U.S. country filter, and JSON output. A successful response is accepted
    only when its postcode and country code match and its coordinates are
    finite and in range. Unresolved matches return ``None``; provider or
    transport failures raise ``GeoapifyProviderError``.
    """
    requested = postcode.strip()
    if not POSTCODE_PATTERN.fullmatch(requested):
        return None

    api_key = get_geoapify_api_key()
    if not api_key:
        raise GeoapifyConfigurationError("Geoapify lookup is not configured.")

    params = {
        "text": requested,
        "type": "postcode",
        "filter": "countrycode:us",
        "format": "json",
        "apiKey": api_key,
    }
    try:
        response = httpx.get(GEOCODING_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 401:
            raise GeoapifyAuthenticationError("Geoapify rejected the configured API key.") from error
        raise GeoapifyProviderError("Geoapify lookup failed.") from error
    except (httpx.HTTPError, TypeError, ValueError) as error:
        raise GeoapifyProviderError("Geoapify lookup failed.") from error

    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise GeoapifyProviderError("Geoapify lookup failed.")

    for result in results:
        if not isinstance(result, dict):
            continue
        result_postcode = result.get("postcode")
        country_code = result.get("country_code")
        if not isinstance(result_postcode, str) or not isinstance(country_code, str):
            continue
        if result_postcode.strip().upper() != requested.upper() or country_code.lower() != "us":
            continue
        latitude = _coordinate(result.get("lat"), -90, 90)
        longitude = _coordinate(result.get("lon"), -180, 180)
        if latitude is None or longitude is None:
            continue

        location: LocationResponse = {
            "postcode": result_postcode.strip(),
            "country_code": "us",
            "latitude": latitude,
            "longitude": longitude,
        }
        locality = _locality(result)
        if locality:
            location["locality"] = locality
        return location

    return None


def _distance_meters(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    radius = 6_371_000
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    haversine = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(min(1.0, haversine)))


def lookup_nearby_hotels(location: LocationResponse) -> list[NearbyHotel]:
    """Return named Geoapify hotel places within 5 km of a verified postcode."""
    api_key = get_geoapify_api_key()
    if not api_key:
        raise GeoapifyConfigurationError("Geoapify lookup is not configured.")

    latitude = location["latitude"]
    longitude = location["longitude"]
    params = {
        "categories": "accommodation.hotel",
        "filter": f"circle:{longitude},{latitude},{HOTEL_RADIUS_METERS}",
        "limit": 20,
        "apiKey": api_key,
    }
    try:
        response = httpx.get(PLACES_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 401:
            raise GeoapifyAuthenticationError("Geoapify rejected the configured API key.") from error
        raise GeoapifyProviderError("Geoapify hotel lookup failed.") from error
    except (httpx.HTTPError, TypeError, ValueError) as error:
        raise GeoapifyProviderError("Geoapify hotel lookup failed.") from error

    features = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(features, list):
        raise GeoapifyProviderError("Geoapify hotel lookup failed.")

    hotels: list[NearbyHotel] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            continue
        name = properties.get("name")
        coordinates = geometry.get("coordinates")
        if not isinstance(name, str) or not name.strip() or not isinstance(coordinates, list) or len(coordinates) < 2:
            continue
        hotel_longitude = _coordinate(coordinates[0], -180, 180)
        hotel_latitude = _coordinate(coordinates[1], -90, 90)
        if hotel_latitude is None or hotel_longitude is None:
            continue
        distance = _distance_meters(latitude, longitude, hotel_latitude, hotel_longitude)
        if distance > HOTEL_RADIUS_METERS:
            continue
        hotel: NearbyHotel = {
            "name": name.strip(),
            "distance_meters": round(distance),
            "latitude": hotel_latitude,
            "longitude": hotel_longitude,
        }
        provider_id = properties.get("place_id")
        if isinstance(provider_id, str) and provider_id.strip():
            # Keep the provider identifier verbatim; it is the local primary key.
            hotel["provider_id"] = provider_id
        address = properties.get("address_line1") or properties.get("formatted")
        if isinstance(address, str) and address.strip():
            hotel["address"] = address.strip()
        locality = _locality(properties)
        if locality:
            hotel["locality"] = locality
        hotels.append(hotel)
    return hotels


def lookup_postcode_with_hotels(postcode: str = "16802") -> LocationResponse | None:
    """Resolve a U.S. postcode, then search hotels around that resolved point."""
    location = lookup_postcode(postcode)
    if location is None:
        return None
    location["hotels"] = lookup_nearby_hotels(location)
    return location
