from dataclasses import replace

import pytest

from agripilot import catalog, db
from agripilot.engine import finance
from agripilot.pipeline import compare_crops, run_analysis


def test_full_analysis_without_any_api_keys(farm, rice_costs, weather):
    """The whole product must work with no LLM key and no weather key."""
    analysis = run_analysis(farm, rice_costs, use_llm=True, weather=weather)
    assert 0 <= analysis.decision_score <= 100
    assert analysis.decision_label in {"Recommended", "Proceed with caution", "Not recommended"}
    assert analysis.ai_explanation, "an explanation must always be produced"
    assert analysis.ai_next_steps, "next steps must always be produced (PRD §17)"
    assert analysis.ai_source == "deterministic"


def test_weather_falls_back_to_mock_without_a_key(farm):
    from agripilot.services import weather as weather_service

    summary = weather_service.get(farm)
    assert summary.source == "mock"
    assert "demo data" in weather_service.source_label(summary)


@pytest.mark.parametrize("province", ["Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan"])
def test_three_crops_in_every_province_run_clean(farm, weather, province):
    local = replace(farm, province=province, district=catalog.districts(province)[0])
    crop_ids = [c.id for c in catalog.crops_for_province(province)][:3]
    assert crop_ids, f"{province} has no crops in the knowledge base"
    for crop_id in crop_ids:
        crop = catalog.crop(crop_id)
        analysis = run_analysis(
            replace(local, planned_crop=crop_id), finance.default_costs_for(crop),
            use_llm=False, weather=weather,
        )
        assert 0 <= analysis.decision_score <= 100


def test_comparison_costs_each_crop_on_its_own_inputs(farm, weather):
    rows = compare_crops(farm, weather, ["rice", "wheat", "chickpea"])
    assert len(rows) == 3
    costs = {r["crop_id"]: r["cost"] for r in rows}
    assert costs["rice"] != costs["chickpea"]     # not sharing one cost sheet
    assert [r["suitability"] for r in rows] == sorted(
        (r["suitability"] for r in rows), reverse=True
    )


def test_analysis_survives_a_database_roundtrip(farm, rice_costs, weather, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    analysis = run_analysis(farm, rice_costs, use_llm=False, weather=weather)
    analysis_id = db.save(analysis)
    assert analysis_id is not None

    loaded = db.get(analysis_id)
    assert loaded is not None
    assert loaded.decision_score == analysis.decision_score
    assert loaded.farm.sowing_date == analysis.farm.sowing_date
    assert loaded.crop.name == analysis.crop.name
    assert len(loaded.climate_risks) == len(analysis.climate_risks)
    assert db.recent(5)[0]["farm_name"] == farm.name
