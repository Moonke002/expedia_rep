"""OpenAI SDK client factory using this project's explicit environment names."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import get_openai_api_key
from .database import StoreError

if TYPE_CHECKING:
    from openai import OpenAI


def create_openai_client() -> OpenAI | None:
    """Pass the custom OPEN_AI value explicitly; the SDK will not infer it."""
    api_key = get_openai_api_key()
    if api_key is None:
        return None
    try:
        from openai import OpenAI
    except ImportError as error:
        raise StoreError("The OpenAI SDK is unavailable in this backend environment.", 503) from error

    return OpenAI(api_key=api_key)
