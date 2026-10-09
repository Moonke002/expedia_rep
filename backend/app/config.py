"""Backend configuration loaded from the project-root environment file."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
# The project-root .env is the source of truth for this local classroom app.
# Override inherited shell values so a stale provider key cannot shadow the
# distinct credentials that the student configured in this file.
load_dotenv(dotenv_path=ENV_FILE, override=True)

DEFAULT_OPENAI_MODEL = "gpt-6-luna"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL


def get_geoapify_api_key() -> str | None:
    """Return the trimmed Geoapify key for backend provider requests only."""
    key = os.getenv("GEOAPIFY_API_KEY", "").strip()
    return key or None


def geoapify_status() -> str:
    """Return configuration status without exposing the API key."""
    return "key is configured" if get_geoapify_api_key() else "key is not configured"


def get_openai_api_key() -> str | None:
    """Return the explicitly named OpenAI key from the project-root environment."""
    key = os.getenv("OPEN_AI", "").strip()
    return key or None


def openai_status() -> str:
    """Report key presence without returning or logging its value."""
    return "key is configured" if get_openai_api_key() else "key is not configured"
