"""Crop suitability scoring (PRD §5.2, FR-02).

Weights and penalties are module-level constants so the AI/ML owner can tune
scoring without touching the surrounding logic.
"""
from __future__ import annotations

from datetime import date

from .. import catalog
from ..models import WATER_RANK, CropSpec, Farm, SuitabilityResult, WeatherSummary
from .units import clamp

# --- tunable constants -------------------------------------------------------
WEIGHTS = {"soil": 0.25, "season": 0.25, "water": 0.25, "climate": 0.15, "budget": 0.10}

SOIL_EXACT, SOIL_ADJACENT, SOIL_UNSUITABLE = 100.0, 60.0, 20.0
SEASON_PENALTY_PER_WEEK = 10.0       # points lost per week outside the window
WATER_PENALTY_PER_LEVEL = 30.0       # points lost per availability level short
CLIMATE_PENALTY_PER_DEG = 6.0        # points lost per °C outside the range
BUDGET_FLOOR_RATIO = 0.50            # budget at 50% of cost scores 0
# -----------------------------------------------------------------------------

_REF_YEAR = 2001  # non-leap reference year for MM-DD arithmetic


def _doy(mm_dd: str) -> int:
    month, day = (int(p) for p in mm_dd.split("-"))
    return date(_REF_YEAR, month, day).timetuple().tm_yday


def _circular_gap_days(target: int, start: int, end: int) -> int:
    """Days by which `target` misses the [start, end] window, handling wraparound."""
    if start <= end:
        inside = start <= target <= end
    else:  # window crosses new year, e.g. 11-01 -> 02-15
        inside = target >= start or target <= end
    if inside:
        return 0
    def gap(a: int, b: int) -> int:
        d = abs(a - b)
        return min(d, 365 - d)
    return min(gap(target, start), gap(target, end))


def score_soil(farm: Farm, crop: CropSpec) -> tuple[float, str]:
    label = catalog.soil_label(farm.soil_type)
    if farm.soil_type in crop.suitable_soils:
        return SOIL_EXACT, f"{label} soil is listed as suitable for {crop.name.lower()}."
    adjacent = catalog.soil_adjacency().get(farm.soil_type, [])
    if any(s in crop.suitable_soils for s in adjacent):
        return SOIL_ADJACENT, (
            f"{label} soil is not ideal for {crop.name.lower()} but is close in texture "
            "to a soil that is."
        )
    return SOIL_UNSUITABLE, (
        f"{label} soil is outside the preferred range for {crop.name.lower()} "
        f"({', '.join(catalog.soil_label(s) for s in crop.suitable_soils)})."
    )


def score_season(farm: Farm, crop: CropSpec) -> tuple[float, str]:
    target = farm.sowing_date.timetuple().tm_yday
    gap = _circular_gap_days(target, _doy(crop.sowing_window[0]), _doy(crop.sowing_window[1]))
    if gap == 0:
        return 100.0, (
            f"Sowing on {farm.sowing_date:%d %b} falls inside the recommended window "
            f"({crop.sowing_window[0]} to {crop.sowing_window[1]})."
        )
    score = clamp(100.0 - (gap / 7.0) * SEASON_PENALTY_PER_WEEK, 0.0, 100.0)
    return score, (
        f"Sowing on {farm.sowing_date:%d %b} is about {gap} days outside the recommended "
        f"window ({crop.sowing_window[0]} to {crop.sowing_window[1]})."
    )


def score_water(farm: Farm, crop: CropSpec) -> tuple[float, str]:
    have = WATER_RANK.get(farm.water_availability, 2)
    need = WATER_RANK.get(crop.water_tolerance, 2)
    if have >= need:
        return 100.0, (
            f"Water availability ({farm.water_availability}) meets this crop's minimum "
            f"requirement ({crop.water_tolerance})."
        )
    short = need - have
    score = clamp(100.0 - short * WATER_PENALTY_PER_LEVEL, 0.0, 100.0)
    return score, (
        f"Water availability ({farm.water_availability}) is {short} level"
        f"{'s' if short > 1 else ''} below what {crop.name.lower()} normally needs "
        f"({crop.water_tolerance}); seasonal demand is about {crop.water_need_mm:.0f} mm."
    )


def score_climate(crop: CropSpec, weather: WeatherSummary) -> tuple[float, str]:
    low, high = crop.temp_range_c
    avg = weather.avg_temp
    if low <= avg <= high:
        return 100.0, (
            f"Average temperature of {avg:.0f}°C sits inside this crop's comfortable "
            f"range ({low:.0f}-{high:.0f}°C)."
        )
    off = (low - avg) if avg < low else (avg - high)
    score = clamp(100.0 - off * CLIMATE_PENALTY_PER_DEG, 0.0, 100.0)
    direction = "below" if avg < low else "above"
    return score, (
        f"Average temperature of {avg:.0f}°C is {off:.1f}°C {direction} this crop's "
        f"range ({low:.0f}-{high:.0f}°C)."
    )


def score_budget(farm: Farm, crop: CropSpec) -> tuple[float, str]:
    typical_total = sum(crop.typical_cost_per_acre_pkr.values()) * farm.area_acres
    if typical_total <= 0:
        return 100.0, "No typical cost data available for this crop; budget not scored."
    ratio = farm.budget_pkr / typical_total
    if ratio >= 1.0:
        return 100.0, (
            f"Budget of PKR {farm.budget_pkr:,.0f} covers the typical input cost of about "
            f"PKR {typical_total:,.0f} for {farm.area_acres:g} acres."
        )
    # Linear from 100 at ratio 1.0 down to 0 at BUDGET_FLOOR_RATIO.
    span = 1.0 - BUDGET_FLOOR_RATIO
    score = clamp((ratio - BUDGET_FLOOR_RATIO) / span * 100.0, 0.0, 100.0)
    return score, (
        f"Budget of PKR {farm.budget_pkr:,.0f} covers about {ratio * 100:.0f}% of the "
        f"typical input cost (PKR {typical_total:,.0f}) for {farm.area_acres:g} acres."
    )


def score_crop(farm: Farm, crop: CropSpec, weather: WeatherSummary) -> SuitabilityResult:
    """Score one crop 0-100 against this farm. Deterministic, no I/O."""
    soil, soil_why = score_soil(farm, crop)
    season, season_why = score_season(farm, crop)
    water, water_why = score_water(farm, crop)
    climate, climate_why = score_climate(crop, weather)
    budget, budget_why = score_budget(farm, crop)

    total = (
        soil * WEIGHTS["soil"] + season * WEIGHTS["season"] + water * WEIGHTS["water"]
        + climate * WEIGHTS["climate"] + budget * WEIGHTS["budget"]
    )

    warnings: list[str] = []
    if farm.province not in crop.provinces:
        warnings.append(
            f"{crop.name} is not commonly grown in {farm.province}; local advice matters more than usual here."
        )
    if soil <= SOIL_UNSUITABLE:
        warnings.append(f"Soil type is a poor match for {crop.name.lower()}.")
    if water <= 40:
        warnings.append("Water availability is well below this crop's normal requirement.")
    if season <= 40:
        warnings.append("Sowing date is far outside the recommended window.")
    if budget <= 40:
        warnings.append("Stated budget is unlikely to cover typical input costs.")

    return SuitabilityResult(
        crop_id=crop.id, crop_name=crop.name, score=round(total, 1),
        soil_score=round(soil, 1), season_score=round(season, 1),
        water_score=round(water, 1), climate_score=round(climate, 1),
        budget_score=round(budget, 1),
        reasons=[soil_why, season_why, water_why, climate_why, budget_why],
        warnings=warnings,
    )


def rank_crops(
    farm: Farm,
    weather: WeatherSummary,
    crop_list: list[CropSpec] | None = None,
    top_n: int = 5,
    exclude: str | None = None,
) -> list[SuitabilityResult]:
    """Rank candidate crops best-first. Defaults to crops grown in this province."""
    if crop_list is None:
        crop_list = catalog.crops_for_province(farm.province) or list(catalog.crops().values())
    results = [score_crop(farm, c, weather) for c in crop_list if c.id != exclude]
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]
