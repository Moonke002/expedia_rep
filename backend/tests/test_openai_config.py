import sys
from types import ModuleType

from app.config import get_openai_api_key, openai_status
from app.controllers.openai_client import create_openai_client


def test_custom_key_name_is_explicit_and_status_does_not_expose_it(monkeypatch):
    monkeypatch.setenv("OPEN_AI", "demo-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "different-default-name")

    assert get_openai_api_key() == "demo-secret"
    assert openai_status() == "key is configured"
    assert "demo-secret" not in openai_status()


def test_default_sdk_environment_name_is_not_used(monkeypatch):
    monkeypatch.setenv("OPEN_AI", "")
    monkeypatch.setenv("OPENAI_API_KEY", "different-default-name")

    assert get_openai_api_key() is None
    assert openai_status() == "key is not configured"
    assert create_openai_client() is None


def test_custom_key_is_passed_to_sdk_client(monkeypatch):
    received = {}

    class FakeOpenAI:
        def __init__(self, *, api_key):
            received["api_key"] = api_key

    fake_sdk = ModuleType("openai")
    fake_sdk.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_sdk)
    monkeypatch.setenv("OPEN_AI", "demo-secret")

    client = create_openai_client()

    assert isinstance(client, FakeOpenAI)
    assert received == {"api_key": "demo-secret"}
