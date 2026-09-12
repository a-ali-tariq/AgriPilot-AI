"""Report which external services are configured and actually reachable.

    python scripts/check_keys.py

Prints no secret values — only whether each key is present and working.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.disable(logging.CRITICAL)  # the services log their own fallback reasons

from agripilot.config import get_secret, llm_model, llm_provider
from agripilot.services import weather
from agripilot.state import demo_farm


def line(name: str, ok: bool, detail: str) -> None:
    print(f"  {'OK  ' if ok else 'OFF '} {name:<14} {detail}")


print("\nAgriPilot AI — external services\n")

# --- weather ---------------------------------------------------------------
key = get_secret("OPENWEATHER_API_KEY")
if not key:
    line("Weather", False, "no key set — app uses clearly-labelled demo data")
else:
    summary = weather.get(demo_farm())
    if summary.source == "live":
        line("Weather", True,
             f"live · {summary.avg_temp:.0f}C avg, {summary.rainfall_mm_30d:.0f} mm rain")
    else:
        line("Weather", False,
             f"key set ({len(key)} chars) but the call failed — most often a new key "
             "still activating (can take up to 2 hours)")

# --- llm -------------------------------------------------------------------
llm_key = get_secret("LLM_API_KEY")
if not llm_key:
    line("AI text", False, "no key — explanations come from the calculation engine")
else:
    try:
        import google.genai  # noqa: F401
        from agripilot.services.llm import _call_provider

        reply = _call_provider("Reply with the word OK.", "Say OK.")
        line("AI text", bool(reply), f"{llm_provider()} · {llm_model()}"
             if reply else "key set but the call failed")
    except ImportError:
        line("AI text", False,
             "key set but google-genai is not installed — uncomment it in requirements.txt")

# --- vision ----------------------------------------------------------------
line("AI vision", bool(llm_key),
     "shares the AI text key" if llm_key else "no key — image assessment stays unavailable")

print("\nThe app runs fully in every OFF case above. Nothing here is required.\n")
