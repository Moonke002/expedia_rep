"""Backend configuration loaded from the project-root environment file."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_FILE)


def get_geoapify_api_key() -> str | None:
    """Return the trimmed Geoapify key for backend provider requests only."""
    key = os.getenv("GEOAPIFY_API_KEY", "").strip()
    return key or None


def geoapify_status() -> str:
    """Return configuration status without exposing the API key."""
    return "key is configured" if get_geoapify_api_key() else "key is not configured"
