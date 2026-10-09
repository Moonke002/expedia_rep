"""Data shapes shared by the API and the SQLite controller."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class SavedProviderHotel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    provider_id: str = Field(min_length=1, max_length=500)
    name: str | None = None
    address: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @field_validator("provider_id")
    @classmethod
    def provider_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Provider ID cannot be blank.")
        return value


class SavedHotelZipContext(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    postcode: str = Field(pattern=r"^[0-9]{5}$")
    country_code: Literal["us"]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    locality: str | None = None


class SaveProviderHotelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hotel: SavedProviderHotel
    location: SavedHotelZipContext


class TravelAssistantQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("Enter a question.")
        return question


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("Enter a message.")
        return message
