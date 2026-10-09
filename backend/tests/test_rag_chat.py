import json
import sqlite3
from types import SimpleNamespace

import pytest

from app import main
from app.controllers.database import DatabaseController, StoreError
from app.controllers.rag import TravelAssistantController
from app.models import ChatRequest
import app.controllers.rag as rag_module


def _hotel(provider_id="saved-hotel-1"):
    return {
        "provider_id": provider_id,
        "name": "Valley Trail Inn",
        "address": "12 Demo Road",
        "latitude": 40.79,
        "longitude": -77.86,
    }


def _location():
    return {
        "postcode": "16802",
        "country_code": "us",
        "latitude": 40.79,
        "longitude": -77.86,
        "locality": "State College",
    }


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=next(self.outputs))


class FakeOpenAIClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


@pytest.fixture
def saved_database(tmp_path):
    controller = DatabaseController(
        db_path=tmp_path / "expedia.sqlite3",
        legacy_bookings_path=None,
    )
    controller.save_api_hotel(_hotel(), _location())
    return controller


def _night_query(postcode="16802"):
    return (
        "SELECT h.hotel_id, h.name AS hotel_name, z.postcode, z.locality, "
        "n.stay_date, n.nightly_rate_cents, n.rooms_available "
        "FROM saved_hotels h "
        "JOIN demo_hotel_nights n ON n.hotel_id = h.hotel_id "
        "JOIN saved_hotel_zips z ON z.hotel_id = h.hotel_id "
        f"WHERE z.postcode = '{postcode}' "
        "AND n.stay_date >= '2026-10-10' AND n.stay_date < '2026-10-12' "
        "ORDER BY n.stay_date"
    )


def test_chat_endpoint_runs_sql_retrieval_then_grounded_answer(saved_database, monkeypatch):
    fake_client = FakeOpenAIClient([_night_query(), "Valley Trail Inn has $100 demo nights on Oct 10 and 11."])
    monkeypatch.setattr(rag_module, "create_openai_client", lambda: fake_client)
    assistant = TravelAssistantController(saved_database)
    monkeypatch.setattr(main, "travel_assistant", assistant)
    monkeypatch.setattr(main, "controller", saved_database)

    response = main.chat(ChatRequest(
        message="Compare a State College stay from October 10 through checkout October 12."
    ))

    payload = response
    assert payload["reply"].startswith("Valley Trail Inn")
    assert payload["proposed_sql"] == _night_query()
    assert [row["stay_date"] for row in payload["records"]] == ["2026-10-10", "2026-10-11"]
    assert len(fake_client.responses.calls) == 2
    proposal = json.loads(fake_client.responses.calls[0]["input"])
    answer_context = json.loads(fake_client.responses.calls[1]["input"])
    assert proposal["question"].startswith("Compare a State College")
    assert "saved_hotel_zips" in proposal["schema"]
    assert answer_context["validated_sql"] == _night_query()
    assert answer_context["retrieved_records"] == payload["records"]
    history = main.get_chat_conversation(payload["conversation_id"])
    assert [item["role"] for item in history["messages"]] == ["user", "assistant"]
    assert all(item["created_at"] for item in history["messages"])
    assert history["messages"][0]["content"].startswith("Compare a State College")
    assert history["messages"][1]["proposed_sql"] == _night_query()
    assert history["messages"][1]["retrieved_records"] == payload["records"]

    restarted_database = DatabaseController(
        db_path=saved_database.db_path,
        legacy_bookings_path=None,
    )
    restored = restarted_database.get_chat_conversation(payload["conversation_id"])
    assert restored["messages"] == history["messages"]


def test_empty_query_results_still_get_second_grounded_response(saved_database, monkeypatch):
    no_match_sql = "SELECT hotel_id, name FROM saved_hotels WHERE name = 'No Such Hotel'"
    fake_client = FakeOpenAIClient([no_match_sql, "No saved hotels matched that request."])
    monkeypatch.setattr(rag_module, "create_openai_client", lambda: fake_client)
    assistant = TravelAssistantController(saved_database)
    monkeypatch.setattr(main, "travel_assistant", assistant)

    response = main.chat(ChatRequest(message="Find No Such Hotel"))

    assert response["reply"] == "No saved hotels matched that request."
    assert response["records"] == []
    assert len(fake_client.responses.calls) == 2


def test_chat_repairs_a_query_that_uses_the_wrong_locality_column(saved_database, monkeypatch):
    invalid_sql = "SELECT hotel_id, name, locality FROM saved_hotels"
    corrected_sql = (
        "SELECT h.hotel_id, h.name, z.locality, z.postcode "
        "FROM saved_hotels h JOIN saved_hotel_zips z ON z.hotel_id = h.hotel_id "
        "WHERE lower(z.locality) = lower('Glen Mills')"
    )
    fake_client = FakeOpenAIClient([invalid_sql, corrected_sql, "No saved hotel has a Glen Mills locality."])
    monkeypatch.setattr(rag_module, "create_openai_client", lambda: fake_client)
    assistant = TravelAssistantController(saved_database)

    response = assistant.chat("Where is Glen Mills?")

    assert response["proposed_sql"] == corrected_sql
    assert response["records"] == []
    assert len(fake_client.responses.calls) == 3
    repair_context = json.loads(fake_client.responses.calls[1]["input"])
    assert repair_context["rejected_sql"] == invalid_sql
    assert "saved_hotel_zips.locality" in fake_client.responses.calls[1]["instructions"]
    assert json.loads(fake_client.responses.calls[2]["input"])["retrieved_records"] == []


def test_missing_requested_night_is_returned_as_insufficient_data(saved_database, monkeypatch):
    with sqlite3.connect(saved_database.db_path) as connection:
        connection.execute(
            "DELETE FROM demo_hotel_nights WHERE hotel_id = ? AND stay_date = ?",
            ("saved-hotel-1", "2026-10-11"),
        )
    query = _night_query().replace("'2026-10-12'", "'2026-10-13'")
    fake_client = FakeOpenAIClient([query, "The Oct 11 record is missing, so a complete stay total is unavailable."])
    monkeypatch.setattr(rag_module, "create_openai_client", lambda: fake_client)
    assistant = TravelAssistantController(saved_database)
    monkeypatch.setattr(main, "travel_assistant", assistant)

    response = main.chat(ChatRequest(message="Compare October 10 check-in to October 13 checkout."))

    assert [row["stay_date"] for row in response["records"]] == ["2026-10-10", "2026-10-12"]
    assert "missing" in response["reply"]
    assert "every requested night" in fake_client.responses.calls[1]["instructions"]


@pytest.mark.parametrize(("query", "expected_error"), [
    ("DELETE FROM saved_hotels", "The proposed database query was not a single allowed SELECT."),
    (
        "SELECT user_id FROM users",
        "I couldn't safely match that question to the saved hotel data. Try asking about a saved hotel name, ZIP code, or locality.",
    ),
    (
        "SELECT hotel_id FROM saved_hotels; DELETE FROM saved_hotels",
        "The proposed database query was not a single allowed SELECT.",
    ),
])
def test_disallowed_sql_is_rejected_without_changing_database(
    saved_database, monkeypatch, query, expected_error
):
    fake_client = FakeOpenAIClient([query, query, "This response must not be requested."])
    monkeypatch.setattr(rag_module, "create_openai_client", lambda: fake_client)
    assistant = TravelAssistantController(saved_database)
    monkeypatch.setattr(main, "travel_assistant", assistant)

    protected_tables = (
        "hotels", "trips", "users", "bookings", "saved_hotels",
        "saved_hotel_zips", "demo_hotel_nights",
    )
    with sqlite3.connect(saved_database.db_path) as connection:
        before = {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in protected_tables
        }

    with pytest.raises(StoreError) as captured:
        main.chat(ChatRequest(message="Find the saved hotel"))
    assert len(fake_client.responses.calls) == (1 if query.startswith("DELETE") or ";" in query else 2)
    failure_history = saved_database.get_chat_conversation(captured.value.conversation_id)
    assert [item["role"] for item in failure_history["messages"]] == ["user", "error"]
    assert all(item["created_at"] for item in failure_history["messages"])
    assert failure_history["messages"][1]["content"] == expected_error
    if query.startswith("SELECT user_id"):
        assert failure_history["messages"][1]["proposed_sql"] == query
    assert not any(item["role"] == "assistant" for item in failure_history["messages"])
    error_payload = json.loads(main.store_error_handler(None, captured.value).body)
    assert error_payload["conversation_id"] == failure_history["conversation_id"]
    with sqlite3.connect(saved_database.db_path) as connection:
        after = {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in protected_tables
        }
    assert after == before


def test_read_only_query_results_are_bounded(saved_database):
    for index in range(2, 7):
        saved_database.save_api_hotel(_hotel(f"saved-hotel-{index}"), _location())
    query = (
        "SELECT h.hotel_id, n.stay_date FROM saved_hotels h "
        "JOIN demo_hotel_nights n ON n.hotel_id = h.hotel_id "
        "ORDER BY h.hotel_id, n.stay_date"
    )

    assert len(saved_database.execute_assistant_query(query)) == 20


def test_read_only_query_rejects_sqlite_functions(saved_database):
    with pytest.raises(StoreError):
        saved_database.execute_assistant_query("SELECT load_extension('unexpected')")
