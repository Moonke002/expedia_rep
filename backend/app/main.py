from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import OPENAI_MODEL, geoapify_status, openai_status
from .controllers.database import SESSION_DAYS, DatabaseController, StoreError
from .controllers.geocoding import (
    GeoapifyAuthenticationError,
    GeoapifyConfigurationError,
    GeoapifyProviderError,
    lookup_postcode_with_hotels,
)
from .controllers.search import SearchController
from .controllers.rag import TravelAssistantController
from .models import (
    AccountCreate,
    AccountLogin,
    BookingCreate,
    BookingStatusUpdate,
    ChatRequest,
    SaveProviderHotelRequest,
    TravelAssistantQuestion,
)


app = FastAPI(title="Expedia Rep API", description="SQLite-backed travel demo", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)
controller = DatabaseController()
travel_assistant = TravelAssistantController(controller)
SESSION_COOKIE = "expedia_demo_session"


def signed_in_user(request: Request) -> dict:
    user = controller.current_user(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise StoreError("Sign in to manage bookings.", 401)
    return user


@app.exception_handler(StoreError)
def store_error_handler(_request, error: StoreError) -> JSONResponse:
    body = {"detail": str(error)}
    if error.conversation_id:
        body["conversation_id"] = error.conversation_id
    return JSONResponse(status_code=error.status_code, content=body)


@app.get("/health")
@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "geoapify_api_key": geoapify_status(),
        "openai_api_key": openai_status(),
        "openai_model": OPENAI_MODEL,
    }


@app.get("/api/demo/zip-location")
def demo_zip_location(postcode: str = Query(default="16802", pattern=r"^\d{5}$")) -> dict:
    try:
        location = lookup_postcode_with_hotels(postcode)
    except GeoapifyConfigurationError as error:
        raise HTTPException(status_code=503, detail="ZIP lookup is not configured.") from error
    except GeoapifyAuthenticationError as error:
        raise HTTPException(
            status_code=503,
            detail="Geoapify rejected its API key. Update GEOAPIFY_API_KEY in the project-root .env file, then restart FastAPI.",
        ) from error
    except GeoapifyProviderError as error:
        raise HTTPException(status_code=502, detail="ZIP lookup provider failed.") from error
    if location is None:
        raise HTTPException(status_code=404, detail="ZIP code could not be resolved.")
    return location


@app.get("/api/saved-hotels")
def saved_hotels_for_postcode(postcode: str = Query(pattern=r"^[0-9]{5}$")) -> dict:
    return controller.get_saved_hotels_for_postcode(postcode)


@app.post("/api/assistant/ask")
def ask_travel_assistant(request: TravelAssistantQuestion) -> dict:
    return travel_assistant.answer(request.question)


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    """Run SQL proposal, checked read-only retrieval, and grounded answer generation."""
    return travel_assistant.chat(request.message, request.conversation_id)


@app.get("/api/chat/{conversation_id}")
def get_chat_conversation(conversation_id: str) -> dict:
    """Load persisted messages, query evidence, and error entries for one conversation."""
    return controller.get_chat_conversation(conversation_id)


@app.post("/api/saved-hotels")
def save_provider_hotel(request: SaveProviderHotelRequest) -> dict:
    return controller.save_api_hotel(request.hotel.model_dump(), request.location.model_dump())


@app.delete("/api/saved-hotels/{provider_id}")
def delete_saved_hotel(provider_id: str) -> dict:
    if not controller.remove_saved_hotel(provider_id):
        raise HTTPException(status_code=404, detail="Saved hotel was not found.")
    return {"provider_id": provider_id, "removed": True}


@app.post("/api/auth/register", status_code=201)
def register_account(request: AccountCreate) -> dict:
    return {"user": controller.register_account(request.username, request.password, request.display_name)}


@app.post("/api/auth/login")
def login(request: AccountLogin, response: Response) -> dict:
    user, token = controller.login(request.username, request.password)
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True, samesite="lax", path="/"
    )
    return {"user": user}


@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    controller.logout(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")


@app.get("/api/auth/me")
def current_user(request: Request) -> dict:
    return {"user": controller.current_user(request.cookies.get(SESSION_COOKIE))}


@app.get("/api/hotels/search")
def search_hotels(
    request: Request,
    hotel_name: str = Query(default="", description="Blank lists all offered stays."),
) -> dict:
    user = controller.current_user(request.cookies.get(SESSION_COOKIE))
    return SearchController(controller).search(hotel_name, user["user_id"] if user else None)


@app.get("/api/users")
def list_users() -> dict:
    return {"users": controller.list_users()}


@app.get("/api/bookings")
def list_bookings(request: Request) -> dict:
    return {"bookings": controller.list_bookings(signed_in_user(request)["user_id"])}


@app.post("/api/bookings", status_code=201)
def create_booking(request: BookingCreate, http_request: Request) -> dict:
    return controller.create_booking(signed_in_user(http_request)["user_id"], request.trip_id)


@app.patch("/api/bookings/{booking_id}")
def update_booking_status(booking_id: str, request: BookingStatusUpdate, http_request: Request) -> dict:
    return controller.cancel_booking(booking_id, request.status, signed_in_user(http_request)["user_id"])


@app.delete("/api/bookings/{booking_id}", status_code=204)
def delete_test_booking(booking_id: str, request: Request) -> Response:
    controller.delete_test_booking(booking_id, signed_in_user(request)["user_id"])
    return Response(status_code=204)
