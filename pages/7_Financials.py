"""Financial Feasibility — FR-07, PRD §5.6."""
from __future__ import annotations

import streamlit as st

from agripilot import state
from agripilot.engine import finance as finance_engine, score as score_engine
from agripilot.engine.units import fmt_pkr
from agripilot.models import CostInputs
from ui import charts, components, theme

theme.setup("Financials", icon="💰")
state.init_state()
components.sidebar_summary()

st.title("Financial feasibility")
analysis = state.require_analysis("the financial analysis")
components.demo_banner(analysis)

farm, crop, costs = analysis.farm, analysis.crop, analysis.costs

st.markdown("#### Your costs")
st.caption(f"All values are per acre, in PKR. Farm area: {farm.area_acres:g} acres.")

c1, c2, c3, c4 = st.columns(4, gap="small")
with c1:
    seed = st.number_input("Seed", min_value=0.0, value=float(costs.seed), step=500.0)
    fertilizer = st.number_input("Fertilizer", min_value=0.0, value=float(costs.fertilizer), step=500.0)
with c2:
    labor = st.number_input("Labor", min_value=0.0, value=float(costs.labor), step=500.0)
    irrigation = st.number_input("Irrigation", min_value=0.0, value=float(costs.irrigation), step=500.0)
with c3:
    pesticide = st.number_input("Pesticide", min_value=0.0, value=float(costs.pesticide), step=500.0)
    machinery = st.number_input("Machinery", min_value=0.0, value=float(costs.machinery), step=500.0)
with c4:
    other = st.number_input("Other", min_value=0.0, value=float(costs.other), step=500.0)
    price = st.number_input(
        f"Expected price per {crop.yield_unit}", min_value=0.0,
        value=float(costs.expected_price_per_unit or crop.typical_price_pkr), step=100.0,
    )

edited = CostInputs(
    seed=seed, fertilizer=fertilizer, labor=labor, irrigation=irrigation,
    pesticide=pesticide, machinery=machinery, other=other,
    expected_price_per_unit=price,
)

if st.button("Recalculate", type="primary"):
    fin = finance_engine.compute_finance(farm, crop, edited, analysis.suitability, analysis.water)
    decision, label = score_engine.decision_score(
        analysis.suitability, fin, analysis.water, analysis.climate_risk_score
    )
    analysis.costs, analysis.finance = edited, fin
    analysis.decision_score, analysis.decision_label = decision, label
    st.session_state["costs"] = edited
    st.success("Recalculated with your figures.")
    st.rerun()

fin = analysis.finance
st.markdown("---")
st.markdown("#### Estimated outcome")

c1, c2, c3, c4 = st.columns(4, gap="small")
with c1:
    components.scorecard("Total cost", fmt_pkr(fin.total_cost),
                         f"{fmt_pkr(fin.cost_per_acre)} per acre")
with c2:
    components.scorecard("Estimated revenue", fmt_pkr(fin.estimated_revenue),
                         f"{fin.estimated_yield:,.0f} {fin.yield_unit} × "
                         f"{fmt_pkr(fin.price_per_unit)}")
with c3:
    components.scorecard(
        "Estimated profit", fmt_pkr(fin.estimated_profit),
        f"{fmt_pkr(fin.profit_per_acre)} per acre",
        color=theme.SCORE_COLORS["good" if fin.estimated_profit > 0 else "poor"],
    )
with c4:
    components.scorecard(
        "Return on investment", f"{fin.roi_pct:.0f}%",
        "Profit as a share of total cost",
        color=theme.SCORE_COLORS["good" if fin.roi_pct >= 0 else "poor"],
    )

if fin.budget_gap < 0:
    st.error(
        f"**Over budget by {fmt_pkr(abs(fin.budget_gap))}.** Your budget of "
        f"{fmt_pkr(farm.budget_pkr)} covers about "
        f"{farm.budget_pkr / max(fin.cost_per_acre, 1):.1f} of your {farm.area_acres:g} acres "
        f"at {fmt_pkr(fin.cost_per_acre)} per acre."
    )
else:
    st.success(
        f"**Within budget.** {fmt_pkr(fin.budget_gap)} of your "
        f"{fmt_pkr(farm.budget_pkr)} budget is left over."
    )

left, right = st.columns(2, gap="medium")
with left:
    st.plotly_chart(
        charts.cost_breakdown(fin, analysis.costs.breakdown(), farm.area_acres),
        use_container_width=True, config={"displayModeBar": False},
    )
with right:
    st.plotly_chart(
        charts.profit_vs_cost(fin, farm.budget_pkr),
        use_container_width=True, config={"displayModeBar": False},
    )

with st.expander("How the yield estimate is built"):
    st.markdown(
        f"- Typical yield for {crop.name.lower()}: **{crop.typical_yield_per_acre:,.0f} "
        f"{crop.yield_unit} per acre**\n"
        f"- Adjusted by suitability ({analysis.suitability.score:.0f}/100) and water stress "
        f"({analysis.water.stress_level}) → yield factor **{fin.yield_factor:.2f}**\n"
        f"- Estimated yield: **{fin.estimated_yield:,.0f} {crop.yield_unit}** across "
        f"{farm.area_acres:g} acres\n"
        f"- Revenue = yield × price = **{fmt_pkr(fin.estimated_revenue)}**\n"
        f"- Profit = revenue − cost = **{fmt_pkr(fin.estimated_profit)}**"
    )

components.estimate_caption()
components.disclaimer()
