"""Data shapes shared by the API and the SQLite controller."""

from pydantic import BaseModel, ConfigDict


class Hotel(BaseModel):
    hotel_id: str
    hotel_name: str
    city: str
    state: str
    nightly_rate_usd: int


class Trip(BaseModel):
    trip_id: str
    hotel_id: str
    trip_name: str
    check_in: str
    check_out: str


class Traveler(BaseModel):
    user_id: str
    display_name: str


class Booking(BaseModel):
    booking_id: str
    user_id: str
    trip_id: str
    booked_on: str
    status: str
    source: str
    stay: Trip
    hotel: Hotel


class PriceQuote(BaseModel):
    base_nightly_rate_usd: int
    displayed_nightly_rate_usd: float
    matching_searches_today: int
    surge_applied: bool


class StayResult(BaseModel):
    hotel: Hotel
    stay: Trip
    pricing: PriceQuote


class AccountCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""


class AccountLogin(BaseModel):
    username: str
    password: str


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trip_id: str


class BookingStatusUpdate(BaseModel):
    status: str
