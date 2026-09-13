"""The single analysis entry point used by every page and every test.

    farm + costs  ->  weather  ->  suitability  ->  water  ->  climate
                  ->  finance  ->  decision score  ->  (optional) AI explanation
"""
from __future__ import annotations

from datetime import datetime

from . import catalog
from .engine import climate, finance, scenario as scenario_engine, score, suitability, water
from .models import Analysis, CostInputs, Farm, Scenario, WeatherSummary


def run_analysis(
    farm: Farm,
    costs: CostInputs | None = None,
    use_llm: bool = True,
    weather: WeatherSummary | None = None,
    supply_multiplier: float = 1.0,
    crop_id: str | None = None,
) -> Analysis:
    """Run the full deterministic pipeline, then optionally add an AI explanation.

    `use_llm=False` keeps this pure and fast, which is what the What-If sliders use.
    """
    crop = catalog.crop(crop_id or farm.planned_crop)
    if costs is None:
        costs = finance.default_costs_for(crop)

    if weather is None:
        from .services import weather as weather_service  # local: engine stays import-pure
        weather = weather_service.get(farm)

    suit = suitability.score_crop(farm, crop, weather)
    wat = water.compute(farm, crop, weather, supply_multiplier=supply_multiplier)
    risks = climate.assess(farm, crop, weather)
    risk_score = climate.risk_score(risks)
    fin = finance.compute_finance(farm, crop, costs, suit, wat)
    decision, label = score.decision_score(suit, fin, wat, risk_score)
    alternatives = suitability.rank_crops(farm, weather, top_n=5, exclude=crop.id)

    analysis = Analysis(
        farm=farm, costs=costs, crop=crop, weather=weather,
        suitability=suit, finance=fin, water=wat,
        climate_risks=risks, climate_risk_score=risk_score,
        decision_score=decision, decision_label=label,
        alternatives=alternatives,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    if use_llm:
        from .services import llm  # local import keeps the engine SDK-free
        explanation, next_steps, source = llm.explain(analysis)
        analysis.ai_explanation = explanation
        analysis.ai_next_steps = next_steps
        analysis.ai_source = source

    return analysis


def run_scenario(base: Analysis, scen: Scenario, use_llm: bool = False) -> Analysis:
    """Re-run the whole pipeline under scenario adjustments. Never mutates `base`."""
    farm, costs, weather, supply = scenario_engine.apply_scenario(
        base.farm, base.costs, base.weather, scen
    )
    return run_analysis(
        farm, costs, use_llm=use_llm, weather=weather,
        supply_multiplier=supply, crop_id=base.crop.id,
    )


def compare_crops(
    farm: Farm, weather: WeatherSummary, crop_ids: list[str]
) -> list[dict]:
    """Side-by-side rows for the Crop Comparison page (FR-04, PRD §5.3).

    Each crop is costed with its own typical inputs, since comparing crops on
    one crop's cost sheet would be meaningless.
    """
    from .engine import climate, water as water_engine

    rows: list[dict] = []
    for crop_id in crop_ids:
        crop = catalog.crop(crop_id)
        suit = suitability.score_crop(farm, crop, weather)
        wat = water_engine.compute(farm, crop, weather)
        costs = finance.default_costs_for(crop)
        fin = finance.compute_finance(farm, crop, costs, suit, wat)
        risks = climate.assess(farm, crop, weather)
        rows.append({
            "crop_id": crop.id,
            "crop": crop.name,
            "season": ", ".join(crop.seasons),
            "suitability": suit.score,
            "water_mm": wat.seasonal_requirement_mm,
            "water_stress": wat.stress_level,
            "cost": fin.total_cost,
            "yield": fin.estimated_yield,
            "yield_unit": crop.yield_unit,
            "revenue": fin.estimated_revenue,
            "profit": fin.estimated_profit,
            "roi": fin.roi_pct,
            "risk": climate.overall_severity(risks),
            "risk_count": len(risks),
            "duration_days": crop.duration_days,
        })
    rows.sort(key=lambda r: r["suitability"], reverse=True)
    return rows
