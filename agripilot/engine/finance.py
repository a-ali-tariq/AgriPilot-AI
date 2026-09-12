"""Cost, revenue and profit estimation (PRD §5.6, §10, FR-07).

PRD formulas, verbatim:
    Estimated Revenue = Estimated Yield x Expected Market Price
    Estimated Profit  = Estimated Revenue - Total Estimated Cost
"""
from __future__ import annotations

from ..models import CostInputs, CropSpec, Farm, FinanceResult, SuitabilityResult, WaterResult
from .units import clamp

# --- tunable constants -------------------------------------------------------
YIELD_FLOOR = 0.50               # a zero-suitability crop still returns half the base factor
WATER_STRESS_YIELD_PENALTY = 0.40  # full water stress costs 40% of remaining yield
# -----------------------------------------------------------------------------


def default_costs_for(crop: CropSpec) -> CostInputs:
    """Per-acre starting costs pulled from crops.json, for prefilling the form."""
    c = crop.typical_cost_per_acre_pkr
    return CostInputs(
        seed=float(c.get("seed", 0)),
        fertilizer=float(c.get("fertilizer", 0)),
        labor=float(c.get("labor", 0)),
        irrigation=float(c.get("irrigation", 0)),
        pesticide=float(c.get("pesticide", 0)),
        machinery=float(c.get("machinery", 0)),
        other=float(c.get("other", 0)),
        expected_price_per_unit=float(crop.typical_price_pkr),
    )


def total_cost(costs: CostInputs, area_acres: float) -> float:
    """Costs are entered per acre; the total scales with farm area."""
    return costs.per_acre_total() * area_acres


def yield_factor(suitability_score: float, water_stress_score: float) -> float:
    """How much of the crop's typical yield this farm can realistically expect."""
    base = YIELD_FLOOR + (1.0 - YIELD_FLOOR) * (clamp(suitability_score, 0, 100) / 100.0)
    return base * (1.0 - WATER_STRESS_YIELD_PENALTY * clamp(water_stress_score, 0.0, 1.0))


def estimated_yield(
    crop: CropSpec, area_acres: float, suitability_score: float, water_stress_score: float
) -> float:
    return crop.typical_yield_per_acre * area_acres * yield_factor(
        suitability_score, water_stress_score
    )


def estimated_revenue(yield_qty: float, price_per_unit: float) -> float:
    return yield_qty * price_per_unit


def estimated_profit(revenue: float, cost: float) -> float:
    return revenue - cost


def compute_finance(
    farm: Farm,
    crop: CropSpec,
    costs: CostInputs,
    suitability: SuitabilityResult,
    water: WaterResult,
) -> FinanceResult:
    area = max(farm.area_acres, 0.0001)
    factor = yield_factor(suitability.score, water.stress_score)
    qty = crop.typical_yield_per_acre * area * factor

    price = costs.expected_price_per_unit or crop.typical_price_pkr
    revenue = estimated_revenue(qty, price)
    cost = total_cost(costs, area)
    profit = estimated_profit(revenue, cost)

    return FinanceResult(
        total_cost=round(cost, 2),
        cost_per_acre=round(cost / area, 2),
        estimated_yield=round(qty, 1),
        yield_unit=crop.yield_unit,
        estimated_revenue=round(revenue, 2),
        estimated_profit=round(profit, 2),
        profit_per_acre=round(profit / area, 2),
        roi_pct=round((profit / cost * 100.0) if cost > 0 else 0.0, 1),
        budget_gap=round(farm.budget_pkr - cost, 2),
        price_per_unit=round(price, 2),
        yield_factor=round(factor, 3),
    )
