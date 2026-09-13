"""What-If scenario simulation (PRD §5.7, FR-08).

A scenario never mutates the base inputs; it returns adjusted copies, so the
base analysis stays intact for side-by-side comparison.
"""
from __future__ import annotations

from dataclasses import replace

from ..models import Analysis, CostInputs, Farm, Scenario, WeatherSummary
from .units import pct_change

# Metrics shown in the Base vs Scenario table, in display order.
# (label, attribute path, higher_is_better, format)
DIFF_METRICS = [
    ("Estimated yield", "finance.estimated_yield", True, "qty"),
    ("Estimated revenue", "finance.estimated_revenue", True, "pkr"),
    ("Estimated profit", "finance.estimated_profit", True, "pkr"),
    ("Total cost", "finance.total_cost", False, "pkr"),
    ("ROI", "finance.roi_pct", True, "pct"),
    ("Suitability score", "suitability.score", True, "score"),
    ("Water stress", "water.stress_score", False, "ratio"),
    ("Climate risk score", "climate_risk_score", False, "score"),
    ("Farm Decision Score", "decision_score", True, "score"),
]


def _get(obj, path: str):
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


def scale(value: float, pct: float) -> float:
    return value * (1.0 + pct / 100.0)


def apply_scenario(
    farm: Farm, costs: CostInputs, weather: WeatherSummary, scenario: Scenario
) -> tuple[Farm, CostInputs, WeatherSummary, float]:
    """Return adjusted copies plus the water-supply multiplier for water.compute."""
    adj_farm = replace(farm, budget_pkr=scale(farm.budget_pkr, scenario.budget_change_pct))

    adj_costs = replace(
        costs,
        fertilizer=scale(costs.fertilizer, scenario.fertilizer_cost_change_pct),
        labor=scale(costs.labor, scenario.labor_cost_change_pct),
        expected_price_per_unit=scale(costs.expected_price_per_unit, scenario.price_change_pct),
    )

    adj_weather = replace(
        weather,
        avg_temp=weather.avg_temp + scenario.temp_change_c,
        max_temp=weather.max_temp + scenario.temp_change_c,
        min_temp=weather.min_temp + scenario.temp_change_c,
    )

    supply_multiplier = max(0.0, 1.0 + scenario.water_change_pct / 100.0)
    return adj_farm, adj_costs, adj_weather, supply_multiplier


def diff(base: Analysis, sim: Analysis) -> list[dict]:
    """Per-metric base/scenario/delta rows for the comparison table."""
    rows = []
    for label, path, higher_is_better, fmt in DIFF_METRICS:
        old, new = float(_get(base, path)), float(_get(sim, path))
        delta = new - old
        change = pct_change(old, new)
        if delta == 0:
            direction = "flat"
        elif (delta > 0) == higher_is_better:
            direction = "better"
        else:
            direction = "worse"
        rows.append({
            "metric": label, "base": old, "scenario": new,
            "delta": delta, "pct_change": change,
            "direction": direction, "format": fmt,
        })
    return rows
