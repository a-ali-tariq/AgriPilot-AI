"""Secrets and feature flags.

Secrets resolve in this order: Streamlit secrets -> environment variable ->
default. Streamlit is imported lazily so the engine and the test suite never
need it.
"""
from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

# Model ids are retired over time. gemini-2.0-flash now 503s because it no
# longer exists. Check `client.models.list()` if calls start failing.
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = Path(__file__).parent.parent / "agripilot.db"

DISCLAIMER = (
    "AgriPilot AI provides AI-generated and model-based decision-support estimates. "
    "Results may vary depending on actual field conditions, weather, soil conditions, "
    "crop varieties, market prices, and other factors. Recommendations should be "
    "validated with local agricultural experts and current field information before "
    "making major farming decisions."
)

CROP_HEALTH_DISCLAIMER = (
    "This image-based assessment is preliminary and should not be treated as a "
    "definitive diagnosis."
)


SECRETS_PATH = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"


@lru_cache(maxsize=1)
def _secrets_file() -> dict:
    """Read .streamlit/secrets.toml directly.

    Streamlit's own st.secrets only works inside a running app, which would leave
    CLI scripts and tests unable to see a configured key. Reading the file makes
    `python scripts/...` behave the same way the app does.
    """
    try:
        with open(SECRETS_PATH, "rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def get_secret(key: str, default: str = "") -> str:
    """Resolve a secret: st.secrets -> secrets.toml -> environment -> default."""
    try:
        import streamlit as st
        from streamlit.runtime import exists as _runtime_exists

        # Touching st.secrets outside a real script run logs a noisy warning, so
        # only look there when Streamlit is actually running the app.
        if _runtime_exists() and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass

    value = _secrets_file().get(key)
    if value not in (None, ""):
        return str(value)

    return os.environ.get(key, default)


def llm_enabled() -> bool:
    return bool(get_secret("LLM_API_KEY"))


def weather_enabled() -> bool:
    return bool(get_secret("OPENWEATHER_API_KEY"))


def llm_provider() -> str:
    return get_secret("LLM_PROVIDER", "gemini").lower()


def llm_model() -> str:
    return get_secret("LLM_MODEL", DEFAULT_GEMINI_MODEL)


def vision_model() -> str:
    return get_secret("VISION_MODEL", get_secret("LLM_MODEL", DEFAULT_GEMINI_MODEL))
