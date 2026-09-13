"""Report which external services are configured and actually reachable.

    python scripts/check_keys.py

Prints no secret values, only whether each key is present and working.
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


print("\nAgriPilot AI: external services\n")

# --- weather ---------------------------------------------------------------
key = get_secret("OPENWEATHER_API_KEY")
if not key:
    line("Weather", False, "no key set, app uses clearly-labelled demo data")
else:
    summary = weather.get(demo_farm())
    if summary.source == "live":
        line("Weather", True,
             f"live · {summary.avg_temp:.0f}C avg, {summary.rainfall_mm_30d:.0f} mm rain")
    else:
        line("Weather", False,
             f"key set ({len(key)} chars) but the call failed. Most often a new key "
             "still activating (can take up to 2 hours)")

# --- llm -------------------------------------------------------------------
llm_key = get_secret("LLM_API_KEY")
if not llm_key:
    line("AI text", False, "no key, explanations come from the calculation engine")

else:
    try:
        import google.genai  # noqa: F401
        from agripilot.services.llm import _call_provider

        # Call directly rather than through _call_provider, so the actual error
        # can be reported instead of a guess about what went wrong.
        from google import genai
        from google.genai import types

        try:
            # Hold the client in a variable: inlining it lets the object be
            # collected before the request fires, raising "client has been closed".
            client = genai.Client(api_key=llm_key)
            client.models.generate_content(
                model=llm_model(), contents='Return exactly: {"ok": true}',
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            line("AI text", True, f"{llm_provider()} · {llm_model()}")
        except Exception as exc:
            detail = str(exc)
            if "RESOURCE_EXHAUSTED" in detail or "429" in detail:
                reason = ("daily free-tier quota exhausted for this model "
                          "(20 requests/day). Resets at midnight Pacific time")
            elif "API_KEY_INVALID" in detail or "401" in detail:
                reason = "key rejected as invalid" + (
                    ". This is an OAuth access token (AQ...), which expires after a "
                    "short period; a key from aistudio.google.com/apikey does not"
                    if llm_key.startswith("AQ") else "")
            elif "NOT_FOUND" in detail or "404" in detail:
                reason = f"model '{llm_model()}' does not exist for this key"
            elif "UNAVAILABLE" in detail or "503" in detail:
                reason = "model is overloaded right now. Transient, retry shortly"
            else:
                reason = f"call failed: {type(exc).__name__}"
            line("AI text", False, reason)
    except ImportError:
        line("AI text", False,
             "key set but google-genai is not installed. Uncomment it in requirements.txt")

# --- vision ----------------------------------------------------------------
# Vision needs the same key AND the SDK, so reuse the text check rather than
# reporting OK on key presence alone.
from agripilot.services.llm import is_configured

line("AI vision", is_configured(),
     "shares the AI text key and SDK" if is_configured()
     else "unavailable. Image assessment reports itself as such, never guesses")

print("\nThe app runs fully in every OFF case above. Nothing here is required.\n")
