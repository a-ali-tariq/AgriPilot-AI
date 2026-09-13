"""LLM explanations and the dashboard assistant (PRD §7, §8, §17).

Two hard rules, enforced here rather than trusted to the model:
  1. The model receives only engine output. It never computes a number.
  2. If the model is unavailable or misbehaves, we fall back to a deterministic
     explanation built from the engine's own reason strings — the user always
     gets a "why", with or without an API key.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

from ..config import get_secret, llm_model, llm_provider
from ..models import Analysis

log = logging.getLogger(__name__)

TIMEOUT_S = 20
MAX_RETRIES = 2
RETRY_BACKOFF_S = 1.5

SYSTEM_PROMPT = """You are the explanation layer of AgriPilot AI, an agricultural \
decision-support tool for farmers in Pakistan.

Hard rules:
- All numbers are given to you, already calculated. Never compute, re-derive, \
adjust or invent any number. Quote only values present in the JSON.
- Never invent farm details that are not in the JSON.
- Always describe yields, revenue and profit as estimates, never guarantees.
- Write for a non-technical farmer. Plain language, no jargon, no markdown headings.
- Use PKR for money and the units given for yield.
- Explanation must be 150 words or fewer.
- Give 3 to 5 concrete next steps, each one short and actionable.

Return ONLY valid JSON in exactly this shape, with no code fences:
{"explanation": "...", "next_steps": ["...", "..."]}"""


# --------------------------------------------------------------------------
# Prompt payload — engine output only
# --------------------------------------------------------------------------
def build_payload(analysis: Analysis) -> dict[str, Any]:
    a = analysis
    return {
        "farm": {
            "district": a.farm.district, "province": a.farm.province,
            "area_acres": a.farm.area_acres, "soil": a.farm.soil_type,
            "water_availability": a.farm.water_availability,
            "irrigation_method": a.farm.irrigation_method,
            "sowing_date": a.farm.sowing_date.isoformat(),
            "budget_pkr": a.farm.budget_pkr,
        },
        "crop": {"name": a.crop.name, "yield_unit": a.crop.yield_unit},
        "weather": {
            "avg_temp_c": a.weather.avg_temp, "max_temp_c": a.weather.max_temp,
            "min_temp_c": a.weather.min_temp,
            "rainfall_mm_30d": a.weather.rainfall_mm_30d,
            "data_source": a.weather.source,
        },
        "suitability": {
            "score_0_100": a.suitability.score,
            "subscores": a.suitability.subscores(),
            "engine_reasons": a.suitability.reasons,
            "warnings": a.suitability.warnings,
        },
        "water": {
            "seasonal_requirement_mm": a.water.seasonal_requirement_mm,
            "gross_requirement_mm": a.water.gross_requirement_mm,
            "irrigation_events": a.water.irrigation_events,
            "frequency_days": a.water.frequency_days,
            "stress_level": a.water.stress_level,
        },
        "climate_risks": [
            {"name": r.name, "severity": r.severity, "impact": r.impact, "action": r.action}
            for r in a.climate_risks
        ],
        "finance": {
            "estimated_yield": a.finance.estimated_yield,
            "estimated_revenue_pkr": a.finance.estimated_revenue,
            "total_cost_pkr": a.finance.total_cost,
            "estimated_profit_pkr": a.finance.estimated_profit,
            "roi_pct": a.finance.roi_pct,
            "budget_gap_pkr": a.finance.budget_gap,
        },
        "decision": {"score_0_100": a.decision_score, "label": a.decision_label},
        "alternatives": [
            {"crop": alt.crop_name, "score": alt.score} for alt in a.alternatives[:3]
        ],
    }


# --------------------------------------------------------------------------
# Provider seam
# --------------------------------------------------------------------------
def _call_gemini(system: str, user: str) -> Optional[str]:
    """Call Google Gemini. Returns raw text, or None if the SDK/key is missing."""
    api_key = get_secret("LLM_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai                    # lazy: optional dependency
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=llm_model(),
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )
        return response.text
    except ImportError:
        log.warning("google-genai is not installed; uncomment it in requirements.txt")
        return None
    except Exception as exc:
        log.warning("Gemini call failed: %s: %s", type(exc).__name__, exc)
        return None


def is_configured() -> bool:
    """True when a call is worth attempting at all.

    Checks key format too: AI Studio keys start with "AIza". A key starting
    "AQ." is a short-lived ephemeral token that authenticates for a few minutes
    and then fails as invalid — better to skip straight to the engine text than
    to spend three retries discovering that.
    """
    key = get_secret("LLM_API_KEY")
    if not key or not key.startswith("AIza"):
        return False
    if llm_provider() != "gemini":
        return False
    try:
        import google.genai  # noqa: F401
    except ImportError:
        return False
    return True


def _call_provider(system: str, user: str) -> Optional[str]:
    provider = llm_provider()
    if provider == "gemini":
        return _call_gemini(system, user)
    log.warning("LLM_PROVIDER '%s' is not wired up yet; using deterministic output", provider)
    return None


def _parse_json(raw: str) -> Optional[dict]:
    """Parse the model's reply, tolerating ```json fences and stray prose."""
    if not raw:
        return None
    text = re.sub(r"^\s*```(?:json)?|```\s*$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    log.warning("Could not parse LLM response as JSON")
    return None


# --------------------------------------------------------------------------
# Deterministic fallback (PRD §10) — always available, never fails
# --------------------------------------------------------------------------
def deterministic_explanation(analysis: Analysis) -> tuple[str, list[str]]:
    a = analysis
    money = lambda v: f"PKR {v:,.0f}"

    verdict = {
        "Recommended": "looks like a reasonable choice",
        "Proceed with caution": "is workable but carries real risk",
        "Not recommended": "is a poor fit as things stand",
    }[a.decision_label]

    lines = [
        f"Based on your farm data, growing {a.crop.name.lower()} on {a.farm.area_acres:g} acres "
        f"in {a.farm.district} {verdict}. The Farm Decision Score is {a.decision_score:.0f} "
        f"out of 100, with a crop suitability of {a.suitability.score:.0f}.",
        f"On the estimates entered, {a.farm.area_acres:g} acres would cost about "
        f"{money(a.finance.total_cost)} and return about {money(a.finance.estimated_revenue)}, "
        f"leaving an estimated profit of {money(a.finance.estimated_profit)} "
        f"({a.finance.roi_pct:.0f}% return). These are estimates, not guarantees.",
        f"Water stress is rated {a.water.stress_level}: the crop needs roughly "
        f"{a.water.gross_requirement_mm:,.0f} mm of applied water across "
        f"{a.water.irrigation_events} irrigations, about one every {a.water.frequency_days} days.",
    ]
    if a.finance.budget_gap < 0:
        lines.append(
            f"Your stated budget falls short of the estimated cost by "
            f"{money(abs(a.finance.budget_gap))}, so arranging finance or reducing the "
            "planted area should come before sowing."
        )
    if a.climate_risks:
        names = ", ".join(r.name.lower() for r in a.climate_risks)
        lines.append(f"Climate risks identified for this season: {names}.")

    steps: list[str] = []
    if a.finance.budget_gap < 0:
        steps.append(
            f"Cover the {money(abs(a.finance.budget_gap))} budget shortfall, or cut the planted "
            f"area to about {a.farm.budget_pkr / max(a.finance.cost_per_acre, 1):.1f} acres."
        )
    if a.water.stress_level in ("high", "critical"):
        steps.append(
            f"Address water first — at {a.water.stress_level} stress, "
            f"{a.water.savings_tips[0].split('.')[0].lower() if a.water.savings_tips else 'improve irrigation efficiency'}."
        )
    for risk in a.climate_risks[:2]:
        steps.append(f"{risk.name}: {risk.action}")
    if a.alternatives:
        best = a.alternatives[0]
        if best.score > a.suitability.score + 5:
            steps.append(
                f"Compare against {best.crop_name} (suitability {best.score:.0f} vs "
                f"{a.suitability.score:.0f}) before committing."
            )
    steps.append(
        "Confirm current local seed, fertiliser and market prices with your dealer or mandi, "
        "then re-run this analysis with the real numbers."
    )
    steps.append("Validate this plan with your local agriculture extension officer before sowing.")

    return "\n\n".join(lines), steps[:5]


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def explain(analysis: Analysis) -> tuple[str, list[str], str]:
    """Return (explanation, next_steps, source) where source is 'llm' or 'deterministic'."""
    payload = json.dumps(build_payload(analysis), indent=2)
    user = (
        "Here is the completed analysis for one farm. Explain the recommendation and give "
        "next steps.\n\n" + payload
    )

    # Nothing configured means nothing to retry — go straight to the engine text.
    if is_configured():
        for attempt in range(MAX_RETRIES + 1):
            raw = _call_provider(SYSTEM_PROMPT, user)
            if raw is not None:
                parsed = _parse_json(raw)
                if parsed and parsed.get("explanation"):
                    steps = parsed.get("next_steps") or []
                    if isinstance(steps, str):
                        steps = [steps]
                    return str(parsed["explanation"]), [str(s) for s in steps][:5], "llm"
            # A transient failure (503 overload, timeout, unparseable reply) is worth
            # another attempt; only an unconfigured provider is not.
            log.warning("LLM attempt %s of %s failed", attempt + 1, MAX_RETRIES + 1)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_S * (attempt + 1))

    text, steps = deterministic_explanation(analysis)
    return text, steps, "deterministic"


def assistant_answer(question: str, analysis: Analysis, history: list[dict] | None = None) -> str:
    """Dashboard assistant. Answers strictly from the current analysis (PRD §7)."""
    system = (
        "You are the AgriPilot AI assistant. Answer ONLY from the farm analysis JSON given "
        "to you. Never invent farm data or new numbers. If the answer is not in the JSON, "
        "say you do not have that information and suggest which page would show it. "
        "Keep answers under 120 words, plain language. Reply with plain text, not JSON."
    )
    context = json.dumps(build_payload(analysis))
    convo = ""
    for turn in (history or [])[-4:]:
        convo += f"\n{turn.get('role', 'user')}: {turn.get('content', '')}"
    user = f"Farm analysis JSON:\n{context}\n\nConversation so far:{convo}\n\nFarmer's question: {question}"

    raw = _call_provider(system, user)
    if raw:
        return raw.strip()
    return (
        "The AI assistant needs an API key to answer free-form questions. Every number it "
        "would quote is already on the Dashboard, Recommendation, Irrigation, Climate Risk "
        "and Financials pages."
    )
