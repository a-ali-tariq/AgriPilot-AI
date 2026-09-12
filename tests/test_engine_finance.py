import pytest

from agripilot.engine import finance
from agripilot.engine.finance import estimated_profit, estimated_revenue, total_cost
from agripilot.models import CostInputs


def test_prd_formulas_exactly():
    # PRD §10: Revenue = Yield x Price; Profit = Revenue - Cost
    assert estimated_revenue(100, 3400) == 340_000
    assert estimated_profit(340_000, 250_000) == 90_000
    assert estimated_profit(100_000, 250_000) == -150_000


def test_total_cost_scales_with_area():
    costs = CostInputs(seed=1000, fertilizer=2000, labor=3000)
    assert total_cost(costs, 1) == 6000
    assert total_cost(costs, 10) == 60_000


def test_yield_factor_bounds():
    # Perfect conditions return the full typical yield; worst conditions never go below
    # the floor after the water penalty.
    assert finance.yield_factor(100, 0.0) == pytest.approx(1.0)
    assert finance.yield_factor(0, 0.0) == pytest.approx(0.5)
    assert finance.yield_factor(100, 1.0) == pytest.approx(0.6)
    assert finance.yield_factor(0, 1.0) == pytest.approx(0.3)


def test_compute_finance_is_internally_consistent(farm, rice, rice_costs, weather):
    from agripilot.engine import suitability, water

    suit = suitability.score_crop(farm, rice, weather)
    wat = water.compute(farm, rice, weather)
    result = finance.compute_finance(farm, rice, rice_costs, suit, wat)

    assert result.estimated_revenue == pytest.approx(
        result.estimated_yield * result.price_per_unit, rel=1e-3
    )
    assert result.estimated_profit == pytest.approx(
        result.estimated_revenue - result.total_cost, rel=1e-3
    )
    assert result.cost_per_acre == pytest.approx(result.total_cost / farm.area_acres)
    assert result.budget_gap == pytest.approx(farm.budget_pkr - result.total_cost)


def test_default_costs_come_from_crop_data(rice):
    costs = finance.default_costs_for(rice)
    assert costs.seed == rice.typical_cost_per_acre_pkr["seed"]
    assert costs.expected_price_per_unit == rice.typical_price_pkr
