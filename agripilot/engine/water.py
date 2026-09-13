"""Irrigation requirement, schedule and water-stress scoring (PRD §5.4, FR-05)."""
from __future__ import annotations

import math

from .. import catalog
from ..models import (
    IRRIGATION_EFFICIENCY, CropSpec, Farm, WaterResult, WeatherSummary,
)
from .units import clamp, mm_over_area_to_liters

# --- tunable constants -------------------------------------------------------
RAINFALL_EFFECTIVE_FRACTION = 0.75      # share of rainfall reaching the root zone
REFERENCE_SEASONAL_SUPPLY_MM = 1400.0   # gross depth an "adequate" farm can apply
SUPPLY_FACTOR = {"abundant": 1.30, "adequate": 1.00, "limited": 0.65, "scarce": 0.35}
# Typical gross depth applied in a single irrigation event, by method (mm).
EVENT_DEPTH_MM = {
    "flood": 100.0, "furrow": 80.0, "tubewell": 80.0,
    "sprinkler": 50.0, "drip": 20.0, "rainfed": 0.0,
}
STRESS_BANDS = [(0.20, "low"), (0.40, "medium"), (0.65, "high")]  # else "critical"
# -----------------------------------------------------------------------------


def _stress_level(score: float) -> str:
    for threshold, label in STRESS_BANDS:
        if score < threshold:
            return label
    return "critical"


def _savings_tips(farm: Farm, crop: CropSpec, stress_level: str) -> list[str]:
    tips: list[str] = []
    if farm.irrigation_method == "flood":
        tips.append(
            "Flood irrigation loses roughly half the applied water. Laser land levelling or "
            "switching to furrow irrigation typically saves 20-30%."
        )
    if farm.irrigation_method in ("flood", "furrow", "tubewell") and stress_level in ("high", "critical"):
        tips.append(
            "At this stress level, drip or sprinkler irrigation would cut gross water use by "
            "roughly a third for the same crop."
        )
    if farm.soil_type in ("sandy", "sandy_loam"):
        tips.append(
            "Sandy soils drain fast. Apply water more often in smaller doses, and mulch to "
            "reduce evaporation loss."
        )
    if farm.soil_type in ("clay", "clay_loam"):
        tips.append(
            "Heavy soils hold water well. Longer intervals between irrigations reduce waste "
            "and lower the risk of waterlogging."
        )
    if crop.water_need_mm >= 1000:
        tips.append(
            f"{crop.name} is a high-water crop ({crop.water_need_mm:.0f} mm per season). "
            "Alternate wetting and drying can save water without a large yield penalty."
        )
    tips.append("Irrigate in the early morning or evening to cut evaporation losses.")
    return tips


def compute(
    farm: Farm,
    crop: CropSpec,
    weather: WeatherSummary,
    supply_multiplier: float = 1.0,
) -> WaterResult:
    """Seasonal water balance for this farm/crop/weather combination.

    `supply_multiplier` scales how much water the farm can actually deliver. The
    What-If simulator uses it to model a continuous change in availability without
    having to jump between the four discrete availability labels.
    """
    soil_factor = catalog.soil_water_factor(farm.soil_type)
    efficiency = IRRIGATION_EFFICIENCY.get(farm.irrigation_method, 0.6)

    net_requirement_mm = crop.water_need_mm * soil_factor

    # Project the 30-day observed rainfall across the growing season.
    seasonal_rain_mm = weather.rainfall_mm_30d * (crop.duration_days / 30.0)
    effective_rain_mm = min(
        seasonal_rain_mm * RAINFALL_EFFECTIVE_FRACTION, net_requirement_mm
    )

    irrigation_need_mm = max(0.0, net_requirement_mm - effective_rain_mm)
    gross_requirement_mm = irrigation_need_mm / efficiency if efficiency > 0 else irrigation_need_mm

    supply_mm = (
        REFERENCE_SEASONAL_SUPPLY_MM
        * SUPPLY_FACTOR.get(farm.water_availability, 1.0)
        * max(supply_multiplier, 0.0)
    )
    stress_score = (
        clamp((gross_requirement_mm - supply_mm) / gross_requirement_mm, 0.0, 1.0)
        if gross_requirement_mm > 0 else 0.0
    )

    depth = EVENT_DEPTH_MM.get(farm.irrigation_method, 80.0)
    if depth > 0 and gross_requirement_mm > 0:
        events = max(1, math.ceil(gross_requirement_mm / depth))
    else:
        events = 0
    frequency_days = int(round(crop.duration_days / events)) if events else 0

    # Split the season's water across growth stages, weighted by kc x duration.
    stages = crop.growth_stages or [{"name": "Whole season", "days": crop.duration_days, "kc": 1.0}]
    weights = [float(s.get("kc", 1.0)) * float(s.get("days", 0)) for s in stages]
    total_weight = sum(weights) or 1.0
    schedule: list[dict] = []
    for stage, weight in zip(stages, weights):
        share = weight / total_weight
        stage_mm = gross_requirement_mm * share
        stage_events = max(1, round(events * share)) if events else 0
        schedule.append({
            "stage": stage.get("name", "Stage"),
            "days": int(stage.get("days", 0)),
            "kc": float(stage.get("kc", 1.0)),
            "water_mm": round(stage_mm, 1),
            "events": stage_events,
            "liters": round(mm_over_area_to_liters(stage_mm, farm.area_acres)),
        })

    level = _stress_level(stress_score)
    return WaterResult(
        seasonal_requirement_mm=round(net_requirement_mm, 1),
        gross_requirement_mm=round(gross_requirement_mm, 1),
        seasonal_requirement_liters=round(mm_over_area_to_liters(gross_requirement_mm, farm.area_acres)),
        effective_rainfall_mm=round(effective_rain_mm, 1),
        irrigation_events=events,
        frequency_days=frequency_days,
        stress_level=level,
        stress_score=round(stress_score, 3),
        savings_tips=_savings_tips(farm, crop, level),
        stage_schedule=schedule,
    )
