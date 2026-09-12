"""Service-layer behaviour with no API keys configured — the deployed default."""
from __future__ import annotations

import io

import pytest

from agripilot.engine import scenario as scenario_engine
from agripilot.models import Scenario
from agripilot.pipeline import compare_crops, run_analysis, run_scenario
from agripilot.services import llm, vision
from agripilot.services.report import build_pdf
from agripilot.services.vision import ImageValidationError


# --- llm ---------------------------------------------------------------------
def test_llm_falls_back_to_deterministic_text(farm, rice_costs, weather):
    analysis = run_analysis(farm, rice_costs, use_llm=False, weather=weather)
    text, steps, source = llm.explain(analysis)
    assert source == "deterministic"
    assert len(text) > 200
    assert 1 <= len(steps) <= 5
    assert "estimates, not guarantees" in text


def test_llm_payload_contains_only_engine_output(farm, rice_costs, weather):
    analysis = run_analysis(farm, rice_costs, use_llm=False, weather=weather)
    payload = llm.build_payload(analysis)
    assert payload["finance"]["estimated_profit_pkr"] == analysis.finance.estimated_profit
    assert payload["decision"]["score_0_100"] == analysis.decision_score
    # The farm name is never sent to the model (PRD §9).
    assert "name" not in payload["farm"]


@pytest.mark.parametrize("raw,expected", [
    ('{"explanation":"a","next_steps":["b"]}', "a"),
    ('```json\n{"explanation":"a","next_steps":["b"]}\n```', "a"),
    ('Sure!\n{"explanation":"a","next_steps":["b"]}\nHope that helps', "a"),
])
def test_json_parser_tolerates_fences_and_prose(raw, expected):
    assert llm._parse_json(raw)["explanation"] == expected


def test_json_parser_returns_none_for_junk():
    assert llm._parse_json("no json here") is None
    assert llm._parse_json("") is None


# --- vision ------------------------------------------------------------------
def _png(width: int = 200, height: int = 200) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (40, 120, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_valid_png_passes_validation():
    mime, size = vision.validate_image(_png(), "image/png")
    assert mime == "image/png"
    assert size == (200, 200)


def test_oversized_image_rejected():
    with pytest.raises(ImageValidationError, match="limit"):
        vision.validate_image(b"x" * (vision.MAX_BYTES + 1), "image/png")


def test_non_image_rejected():
    with pytest.raises(ImageValidationError):
        vision.validate_image(b"this is not an image at all", "image/png")


def test_wrong_mime_type_rejected():
    with pytest.raises(ImageValidationError, match="not a supported image type"):
        vision.validate_image(_png(), "image/gif")


def test_tiny_image_rejected():
    with pytest.raises(ImageValidationError, match="too small"):
        vision.validate_image(_png(16, 16), "image/png")


def test_assessment_without_a_key_never_invents_a_diagnosis():
    result = vision.assess_image(_png(), "image/png")
    assert result["available"] is False
    assert result["confidence"] == 0.0
    assert result["symptoms"] == []
    assert vision.CROP_HEALTH_DISCLAIMER in result["disclaimer"]


# --- report ------------------------------------------------------------------
def test_pdf_contains_every_section(farm, rice_costs, weather):
    analysis = run_analysis(farm, rice_costs, use_llm=True, weather=weather)
    comparison = compare_crops(farm, weather, ["rice", "wheat", "chickpea"])
    simulated = run_scenario(analysis, Scenario(water_change_pct=-20, temp_change_c=3))
    pdf = build_pdf(
        analysis, comparison=comparison,
        scenario_diff=scenario_engine.diff(analysis, simulated),
        crop_health={"available": True, "condition": "Leaf blight", "confidence": 0.6,
                     "severity": "moderate", "symptoms": ["brown lesions"]},
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 8000
    assert pdf.count(b"/Type /Page") >= 2


def test_pdf_builds_with_only_the_required_sections(farm, rice_costs, weather):
    analysis = run_analysis(farm, rice_costs, use_llm=True, weather=weather)
    pdf = build_pdf(analysis)
    assert pdf.startswith(b"%PDF")
