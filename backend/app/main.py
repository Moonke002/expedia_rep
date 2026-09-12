import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Expedia Rep API",
    description="Backend API for the Expedia Rep project.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parents[1]
HOTELS_FILE = DATA_DIR / "hotels.csv"
TRIPS_FILE = DATA_DIR / "trips.csv"
HOTEL_NAME_COLUMNS = ("hotel_name", "name", "hotel")


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


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple liveness response."""
    return {"status": "ok"}


@app.get("/api/hotels/search")
def search_hotels(
    hotel_name: str = Query(min_length=1, description="Hotel name to search for."),
) -> dict[str, Any]:
    """Return matching hotels joined to their available stays by hotel_id."""
    query = hotel_name.strip()
    if not query:
        return {"query": "", "results": []}

    results = _search_results(query)
    return {"query": query, "results": results}
