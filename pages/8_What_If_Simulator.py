"""What-If Simulator — FR-08, PRD §5.7. The key differentiating feature."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from agripilot import state
from agripilot.engine import scenario as scenario_engine
from agripilot.engine.units import fmt_pkr
from agripilot.models import Scenario
from agripilot.pipeline import run_scenario
from ui import charts, components, theme

theme.setup("What-If Simulator", icon="🔬")
state.init_state()
components.sidebar_summary()

st.title("What-If simulator")
analysis = state.require_analysis("the simulator")
components.demo_banner(analysis)

st.caption(
    "Change the conditions and see how the same farm performs. Every number is recalculated "
    "by the same engine — nothing is estimated by the AI model."
)

PRD_EXAMPLE = Scenario(
    water_change_pct=-20.0, temp_change_c=3.0,
    fertilizer_cost_change_pct=15.0, price_change_pct=-10.0,
)

col_a, col_b = st.columns([1, 1])
with col_a:
    if st.button("Load example scenario", use_container_width=True,
                 help="−20% water, +3°C, +15% fertilizer cost, −10% crop price"):
        st.session_state["scenario"] = PRD_EXAMPLE
        st.rerun()
with col_b:
    if st.button("Reset to base", use_container_width=True):
        st.session_state["scenario"] = Scenario()
        st.rerun()

current = state.get_scenario()

st.markdown("#### Conditions")
c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    water_change = st.slider("Water availability", -50, 50, int(current.water_change_pct),
                             step=5, format="%d%%")
    temp_change = st.slider("Temperature", -5.0, 5.0, float(current.temp_change_c),
                            step=0.5, format="%.1f °C")
with c2:
    fert_change = st.slider("Fertilizer cost", -30, 50,
                            int(current.fertilizer_cost_change_pct), step=5, format="%d%%")
    labor_change = st.slider("Labor cost", -30, 50, int(current.labor_cost_change_pct),
                             step=5, format="%d%%")
with c3:
    price_change = st.slider("Crop price", -40, 40, int(current.price_change_pct),
                             step=5, format="%d%%")
    budget_change = st.slider("Budget", -50, 50, int(current.budget_change_pct),
                              step=5, format="%d%%")

scenario = Scenario(
    water_change_pct=water_change, temp_change_c=temp_change,
    fertilizer_cost_change_pct=fert_change, labor_cost_change_pct=labor_change,
    price_change_pct=price_change, budget_change_pct=budget_change,
)
st.session_state["scenario"] = scenario

if scenario.is_baseline():
    st.info("Move a slider to simulate a change. Everything currently matches the base analysis.")
    components.disclaimer()
    st.stop()

# use_llm=False keeps the sliders responsive; the engine alone produces every number.
simulated = run_scenario(analysis, scenario, use_llm=False)
st.session_state["scenario_analysis"] = simulated
rows = scenario_engine.diff(analysis, simulated)
st.session_state["scenario_diff"] = rows

st.markdown("---")
st.markdown("#### Base vs scenario")

c1, c2, c3 = st.columns(3, gap="small")
profit_row = next(r for r in rows if r["metric"] == "Estimated profit")
score_row = next(r for r in rows if r["metric"] == "Farm Decision Score")
with c1:
    components.scorecard(
        "Estimated profit", fmt_pkr(simulated.finance.estimated_profit),
        f"Base {fmt_pkr(analysis.finance.estimated_profit)} · "
        f"{profit_row['pct_change']:+.1f}%",
        color=theme.SCORE_COLORS["good" if profit_row["direction"] == "better" else "poor"],
    )
with c2:
    components.scorecard(
        "Farm Decision Score", f"{simulated.decision_score:.0f}/100",
        f"Base {analysis.decision_score:.0f} · {simulated.decision_label}",
        color=theme.score_color(simulated.decision_score),
    )
with c3:
    components.scorecard(
        "Water stress", simulated.water.stress_level.title(),
        f"Base {analysis.water.stress_level} · index {simulated.water.stress_score:.2f}",
        color=theme.SEVERITY_COLORS.get(simulated.water.stress_level, theme.MUTED),
    )


def _fmt(value: float, kind: str) -> str:
    if kind == "pkr":
        return f"{value:,.0f}"
    if kind == "pct":
        return f"{value:.1f}%"
    if kind == "ratio":
        return f"{value:.2f}"
    return f"{value:,.1f}"


table = pd.DataFrame([{
    "Metric": r["metric"],
    "Base": _fmt(r["base"], r["format"]),
    "Scenario": _fmt(r["scenario"], r["format"]),
    "Change": f"{r['pct_change']:+.1f}%" if r["base"] else "—",
    "Direction": {"better": "Better", "worse": "Worse", "flat": "No change"}[r["direction"]],
} for r in rows])

st.dataframe(table, use_container_width=True, hide_index=True)
components.estimate_caption()

st.plotly_chart(charts.scenario_delta_bars(rows), use_container_width=True,
                config={"displayModeBar": False})

changes = []
if water_change:
    changes.append(f"water availability {water_change:+d}%")
if temp_change:
    changes.append(f"temperature {temp_change:+.1f}°C")
if fert_change:
    changes.append(f"fertilizer cost {fert_change:+d}%")
if labor_change:
    changes.append(f"labor cost {labor_change:+d}%")
if price_change:
    changes.append(f"crop price {price_change:+d}%")
if budget_change:
    changes.append(f"budget {budget_change:+d}%")

st.markdown("#### What this scenario means")
st.markdown(
    f"With {', '.join(changes)}, estimated profit moves from "
    f"**{fmt_pkr(analysis.finance.estimated_profit)}** to "
    f"**{fmt_pkr(simulated.finance.estimated_profit)}** "
    f"({profit_row['pct_change']:+.1f}%), and the Farm Decision Score moves from "
    f"**{analysis.decision_score:.0f}** to **{simulated.decision_score:.0f}** "
    f"(*{simulated.decision_label}*)."
)
if simulated.water.stress_level != analysis.water.stress_level:
    st.warning(
        f"Water stress changes from **{analysis.water.stress_level}** to "
        f"**{simulated.water.stress_level}** under this scenario."
    )
new_risks = {r.name for r in simulated.climate_risks} - {r.name for r in analysis.climate_risks}
if new_risks:
    st.warning(f"New climate risk in this scenario: {', '.join(sorted(new_risks))}.")

if st.button("Explain this scenario with AI"):
    from agripilot.services import llm
    with st.spinner("Asking the AI model…"):
        text, steps, source = llm.explain(simulated)
    st.markdown(text)
    if source != "llm":
        st.caption("Generated by the calculation engine — the AI model was unavailable.")

components.disclaimer()
