"""Farm Decision Score aggregation (PRD §5.9)."""
from __future__ import annotations

from ..models import FinanceResult, SuitabilityResult, WaterResult
from .units import clamp

# --- tunable constants -------------------------------------------------------
WEIGHTS = {"suitability": 0.40, "finance": 0.30, "water": 0.15, "climate": 0.15}
OVER_BUDGET_PENALTY = 15.0       # points off finance_score when cost exceeds budget
RECOMMENDED_AT = 70.0
CAUTION_AT = 45.0
# -----------------------------------------------------------------------------


def finance_score(finance: FinanceResult) -> float:
    """Map ROI onto 0-100: break-even scores 50, +50% ROI scores 100."""
    score = clamp(50.0 + finance.roi_pct, 0.0, 100.0)
    if finance.budget_gap < 0:
        score = clamp(score - OVER_BUDGET_PENALTY, 0.0, 100.0)
    return score


def label_for(score: float) -> str:
    if score >= RECOMMENDED_AT:
        return "Recommended"
    if score >= CAUTION_AT:
        return "Proceed with caution"
    return "Not recommended"


def decision_score(
    suitability: SuitabilityResult,
    finance: FinanceResult,
    water: WaterResult,
    climate_risk_score: float,
) -> tuple[float, str]:
    total = (
        suitability.score * WEIGHTS["suitability"]
        + finance_score(finance) * WEIGHTS["finance"]
        + (100.0 - water.stress_score * 100.0) * WEIGHTS["water"]
        + (100.0 - clamp(climate_risk_score, 0.0, 100.0)) * WEIGHTS["climate"]
    )
    total = round(clamp(total, 0.0, 100.0), 1)
    return total, label_for(total)
