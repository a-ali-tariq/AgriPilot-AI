"""Dataclasses shared by the engine, services and UI.

These are plain dataclasses on purpose: they serialise to JSON for the DB, the
PDF report and the LLM prompt without any framework in the way.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Literal, Optional

SoilType = Literal["loamy", "clay", "sandy", "silty", "clay_loam", "sandy_loam"]
WaterAvailability = Literal["abundant", "adequate", "limited", "scarce"]
IrrigationMethod = Literal["flood", "furrow", "sprinkler", "drip", "rainfed", "tubewell"]
Province = Literal["Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan"]
Severity = Literal["low", "medium", "high"]

# Ordered worst -> best so a rank comparison is just an index lookup.
WATER_RANK: dict[str, int] = {"scarce": 1, "limited": 2, "adequate": 3, "abundant": 4}
RANK_WATER: dict[int, str] = {v: k for k, v in WATER_RANK.items()}

# Share of applied water actually reaching the root zone.
IRRIGATION_EFFICIENCY: dict[str, float] = {
    "flood": 0.50,
    "furrow": 0.60,
    "sprinkler": 0.75,
    "drip": 0.90,
    "tubewell": 0.60,
    "rainfed": 1.00,
}


@dataclass
class Farm:
    name: str
    province: str
    district: str
    area_acres: float
    soil_type: str
    water_availability: str
    irrigation_method: str
    planned_crop: str
    sowing_date: date
    budget_pkr: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    is_demo: bool = False


@dataclass
class CostInputs:
    seed: float = 0.0
    fertilizer: float = 0.0
    labor: float = 0.0
    irrigation: float = 0.0
    pesticide: float = 0.0
    machinery: float = 0.0
    other: float = 0.0
    expected_price_per_unit: float = 0.0  # PKR per yield unit (usually per maund)

    def per_acre_total(self) -> float:
        return (
            self.seed + self.fertilizer + self.labor + self.irrigation
            + self.pesticide + self.machinery + self.other
        )

    def breakdown(self) -> dict[str, float]:
        return {
            "Seed": self.seed, "Fertilizer": self.fertilizer, "Labor": self.labor,
            "Irrigation": self.irrigation, "Pesticide": self.pesticide,
            "Machinery": self.machinery, "Other": self.other,
        }


@dataclass
class CropSpec:
    """One entry from crops.json."""
    id: str
    name: str
    name_ur: str
    seasons: list[str]
    sowing_window: tuple[str, str]      # ("06-01", "07-31"), MM-DD
    duration_days: int
    water_need_mm: float
    water_tolerance: str
    suitable_soils: list[str]
    temp_range_c: tuple[float, float]
    typical_yield_per_acre: float
    yield_unit: str
    typical_price_pkr: float
    typical_cost_per_acre_pkr: dict[str, float]
    provinces: list[str]
    growth_stages: list[dict[str, Any]]
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CropSpec":
        return cls(
            id=d["id"], name=d["name"], name_ur=d.get("name_ur", ""),
            seasons=list(d.get("seasons", [])),
            sowing_window=(d["sowing_window"][0], d["sowing_window"][1]),
            duration_days=int(d["duration_days"]),
            water_need_mm=float(d["water_need_mm"]),
            water_tolerance=d["water_tolerance"],
            suitable_soils=list(d["suitable_soils"]),
            temp_range_c=(float(d["temp_range_c"][0]), float(d["temp_range_c"][1])),
            typical_yield_per_acre=float(d["typical_yield_per_acre"]),
            yield_unit=d.get("yield_unit", "maund"),
            typical_price_pkr=float(d["typical_price_pkr"]),
            typical_cost_per_acre_pkr=dict(d.get("typical_cost_per_acre_pkr", {})),
            provinces=list(d.get("provinces", [])),
            growth_stages=list(d.get("growth_stages", [])),
            notes=d.get("notes", ""),
        )


@dataclass
class WeatherSummary:
    avg_temp: float
    max_temp: float
    min_temp: float
    rainfall_mm_30d: float
    forecast_rain_mm_7d: float
    humidity_pct: float = 50.0
    source: str = "mock"            # "live" | "mock"
    location_label: str = ""


@dataclass
class SuitabilityResult:
    crop_id: str
    crop_name: str
    score: float                     # 0-100
    soil_score: float
    season_score: float
    water_score: float
    climate_score: float
    budget_score: float
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def subscores(self) -> dict[str, float]:
        return {
            "Soil": self.soil_score, "Season": self.season_score,
            "Water": self.water_score, "Climate": self.climate_score,
            "Budget": self.budget_score,
        }


@dataclass
class FinanceResult:
    total_cost: float
    cost_per_acre: float
    estimated_yield: float
    yield_unit: str
    estimated_revenue: float
    estimated_profit: float
    profit_per_acre: float
    roi_pct: float
    budget_gap: float                # budget - total_cost (negative = over budget)
    price_per_unit: float = 0.0
    yield_factor: float = 1.0


@dataclass
class WaterResult:
    seasonal_requirement_mm: float
    gross_requirement_mm: float      # after irrigation-efficiency losses
    seasonal_requirement_liters: float
    effective_rainfall_mm: float
    irrigation_events: int
    frequency_days: int
    stress_level: str                # low | medium | high | critical
    stress_score: float              # 0-1
    savings_tips: list[str] = field(default_factory=list)
    stage_schedule: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ClimateRisk:
    name: str
    severity: str                    # low | medium | high
    probability: float               # 0-1 rule confidence
    impact: str
    action: str


@dataclass
class Scenario:
    water_change_pct: float = 0.0
    temp_change_c: float = 0.0
    fertilizer_cost_change_pct: float = 0.0
    labor_cost_change_pct: float = 0.0
    price_change_pct: float = 0.0
    budget_change_pct: float = 0.0

    def is_baseline(self) -> bool:
        return all(v == 0 for v in asdict(self).values())


@dataclass
class Analysis:
    """Everything the dashboard, simulator and report need, in one object."""
    farm: Farm
    costs: CostInputs
    crop: CropSpec
    weather: WeatherSummary
    suitability: SuitabilityResult
    finance: FinanceResult
    water: WaterResult
    climate_risks: list[ClimateRisk]
    climate_risk_score: float
    decision_score: float
    decision_label: str
    alternatives: list[SuitabilityResult] = field(default_factory=list)
    ai_explanation: Optional[str] = None
    ai_next_steps: Optional[list[str]] = None
    ai_source: str = "deterministic"   # "llm" | "deterministic"
    created_at: str = ""

    @property
    def weather_source(self) -> str:
        return self.weather.source
