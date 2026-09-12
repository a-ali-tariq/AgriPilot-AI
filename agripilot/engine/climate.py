"""Rule-based climate risk identification (PRD §5.5, FR-06).

Each rule is a pure predicate over the farm, crop and weather summary. No
probabilities are invented by a model — they are fixed rule confidences.
"""
from __future__ import annotations

from ..models import WATER_RANK, ClimateRisk, CropSpec, Farm, WeatherSummary

SEVERITY_SCORE = {"low": 25.0, "medium": 55.0, "high": 85.0}

HEAT_MARGIN_C = 3.0          # °C above the crop's max before heat stress is flagged
LOW_RAIN_RATIO = 0.60        # seasonal rainfall below this share of need = drought risk
HEAVY_RAIN_RATIO = 1.50      # forecast rainfall this far above normal = waterlogging


def assess(farm: Farm, crop: CropSpec, weather: WeatherSummary) -> list[ClimateRisk]:
    risks: list[ClimateRisk] = []
    crop_min, crop_max = crop.temp_range_c
    seasonal_rain = weather.rainfall_mm_30d * (crop.duration_days / 30.0)
    have_water = WATER_RANK.get(farm.water_availability, 2)
    need_water = WATER_RANK.get(crop.water_tolerance, 2)

    if weather.max_temp > crop_max + HEAT_MARGIN_C:
        over = weather.max_temp - crop_max
        risks.append(ClimateRisk(
            name="Heat stress",
            severity="high" if over > 6 else "medium",
            probability=0.75,
            impact=(
                f"Maximum temperature of {weather.max_temp:.0f}°C is {over:.0f}°C above the "
                f"upper limit for {crop.name.lower()}. Expect flower or pollen drop and "
                "reduced grain or boll set."
            ),
            action=(
                "Shift sowing earlier or later to move flowering out of peak heat, irrigate in "
                "the evening, and keep soil moisture higher during the flowering stage."
            ),
        ))

    if weather.min_temp < crop_min:
        risks.append(ClimateRisk(
            name="Cold at sowing",
            severity="medium" if weather.min_temp > crop_min - 5 else "high",
            probability=0.6,
            impact=(
                f"Minimum temperature of {weather.min_temp:.0f}°C is below the {crop_min:.0f}°C "
                f"floor for {crop.name.lower()}, which slows and thins germination."
            ),
            action="Delay sowing until temperatures rise, or increase the seed rate to compensate for lower emergence.",
        ))

    if seasonal_rain < crop.water_need_mm * LOW_RAIN_RATIO and have_water <= 2:
        risks.append(ClimateRisk(
            name="Low rainfall / drought",
            severity="high" if have_water == 1 else "medium",
            probability=0.7,
            impact=(
                f"Projected seasonal rainfall of about {seasonal_rain:.0f} mm covers well under "
                f"the {crop.water_need_mm:.0f} mm this crop needs, and irrigation water is "
                f"{farm.water_availability}. Expect water stress and stunted growth."
            ),
            action=(
                "Move to drip or furrow irrigation, mulch to hold soil moisture, and consider a "
                "shorter-duration or drought-tolerant variety."
            ),
        ))

    if weather.forecast_rain_mm_7d > weather.rainfall_mm_30d * HEAVY_RAIN_RATIO / 4:
        risks.append(ClimateRisk(
            name="Heavy rainfall / waterlogging",
            severity="medium",
            probability=0.5,
            impact=(
                f"The 7-day forecast of {weather.forecast_rain_mm_7d:.0f} mm is high relative to "
                "recent rainfall. Standing water raises the risk of root damage and fungal disease."
            ),
            action="Clear drainage channels before the rain, hold off on the next irrigation, and use raised beds where possible.",
        ))

    if have_water == 1 and need_water >= 3:
        risks.append(ClimateRisk(
            name="Water shortage",
            severity="high",
            probability=0.8,
            impact=(
                f"{crop.name} normally needs {crop.water_tolerance} water but availability here is "
                "scarce. This is a crop-failure level mismatch, not just a yield penalty."
            ),
            action=f"Switch to a low-water crop such as chickpea or mustard, or reduce the area under {crop.name.lower()}.",
        ))

    if farm.irrigation_method == "rainfed" and crop.water_need_mm > 600:
        risks.append(ClimateRisk(
            name="Rainfed high-water crop",
            severity="high",
            probability=0.75,
            impact=(
                f"{crop.name} needs about {crop.water_need_mm:.0f} mm per season and there is no "
                "irrigation system to make up a rainfall shortfall."
            ),
            action="Arrange supplementary irrigation, or choose a crop suited to barani (rainfed) conditions.",
        ))

    return risks


def risk_score(risks: list[ClimateRisk]) -> float:
    """Overall 0–100 climate risk. Driven by the worst risk, nudged up by the rest."""
    if not risks:
        return 0.0
    scores = sorted((SEVERITY_SCORE.get(r.severity, 25.0) for r in risks), reverse=True)
    total = scores[0] + sum(s * 0.15 for s in scores[1:])
    return round(min(total, 100.0), 1)


def overall_severity(risks: list[ClimateRisk]) -> str:
    if not risks:
        return "low"
    order = ["low", "medium", "high"]
    return max(risks, key=lambda r: order.index(r.severity)).severity
