import pytest

from agripilot import catalog
from agripilot.engine import finance, scenario as scenario_engine
from agripilot.models import Scenario
from agripilot.pipeline import run_analysis, run_scenario


@pytest.fixture
def base(farm, rice_costs, weather):
    return run_analysis(farm, rice_costs, use_llm=False, weather=weather)


def test_prd_example_scenario_hurts_profit_and_raises_stress(base):
    """PRD §5.7: -20% water, +3°C, +15% fertilizer, -10% price."""
    simulated = run_scenario(
        base, Scenario(water_change_pct=-20, temp_change_c=3,
                       fertilizer_cost_change_pct=15, price_change_pct=-10)
    )
    assert simulated.finance.estimated_profit < base.finance.estimated_profit
    assert simulated.finance.total_cost > base.finance.total_cost
    assert simulated.water.stress_score > base.water.stress_score
    assert simulated.decision_score < base.decision_score


def test_scenario_never_mutates_the_base_analysis(base):
    before = (base.finance.estimated_profit, base.costs.fertilizer,
              base.farm.budget_pkr, base.weather.avg_temp)
    run_scenario(base, Scenario(water_change_pct=-40, fertilizer_cost_change_pct=50,
                                budget_change_pct=-30, temp_change_c=4))
    after = (base.finance.estimated_profit, base.costs.fertilizer,
             base.farm.budget_pkr, base.weather.avg_temp)
    assert before == after


def test_empty_scenario_reproduces_the_base_numbers(base):
    same = run_scenario(base, Scenario())
    assert same.finance.estimated_profit == pytest.approx(base.finance.estimated_profit)
    assert same.decision_score == pytest.approx(base.decision_score)


def test_higher_price_raises_profit(base):
    better = run_scenario(base, Scenario(price_change_pct=20))
    assert better.finance.estimated_revenue > base.finance.estimated_revenue
    assert better.finance.estimated_profit > base.finance.estimated_profit


def test_diff_rows_label_direction_correctly(base):
    worse = run_scenario(base, Scenario(price_change_pct=-25))
    rows = {r["metric"]: r for r in scenario_engine.diff(base, worse)}
    assert rows["Estimated profit"]["direction"] == "worse"
    assert rows["Total cost"]["direction"] == "flat"      # price change does not move cost
    assert len(rows) == len(scenario_engine.DIFF_METRICS)


def test_cost_increase_is_bad_even_though_the_number_goes_up(base):
    dearer = run_scenario(base, Scenario(fertilizer_cost_change_pct=30))
    rows = {r["metric"]: r for r in scenario_engine.diff(base, dearer)}
    assert rows["Total cost"]["pct_change"] > 0
    assert rows["Total cost"]["direction"] == "worse"
