"""Dashboard — PRD §6."""
from __future__ import annotations

import streamlit as st

from agripilot import catalog, db, state
from agripilot.engine import climate as climate_engine
from agripilot.engine.units import fmt_pkr
from ui import charts, components, theme

theme.setup("Dashboard", icon="📊")
state.init_state()
components.sidebar_summary()

st.title("Farm dashboard")
analysis = state.require_analysis("the dashboard")

components.demo_banner(analysis)
components.source_banner(analysis.weather)

farm, fin, wat = analysis.farm, analysis.finance, analysis.water

# --- top row: the four headline numbers --------------------------------------
c1, c2, c3, c4 = st.columns(4, gap="small")
with c1:
    components.score_card("Farm Decision Score", analysis.decision_score, analysis.decision_label)
with c2:
    profit_color = theme.SCORE_COLORS["good" if fin.estimated_profit > 0 else "poor"]
    components.scorecard(
        "Estimated profit", fmt_pkr(fin.estimated_profit),
        f"{fmt_pkr(fin.profit_per_acre)} per acre · {fin.roi_pct:.0f}% ROI",
        color=profit_color,
    )
with c3:
    severity = climate_engine.overall_severity(analysis.climate_risks)
    components.scorecard(
        "Overall climate risk", severity.title(),
        f"{len(analysis.climate_risks)} risk(s) identified"
        if analysis.climate_risks else "No significant risks",
        color=theme.SEVERITY_COLORS.get(severity),
    )
with c4:
    components.scorecard(
        "Water stress", wat.stress_level.title(),
        f"{wat.gross_requirement_mm:,.0f} mm needed · every {wat.frequency_days} days",
        color=theme.SEVERITY_COLORS.get(wat.stress_level, theme.MUTED),
    )

st.markdown("")

# --- second row: gauge + farm overview ---------------------------------------
left, right = st.columns([1, 1.35], gap="medium")
with left:
    st.plotly_chart(
        charts.decision_gauge(analysis.decision_score, analysis.decision_label),
        use_container_width=True, config={"displayModeBar": False},
    )
with right:
    st.markdown("#### Farm overview")
    a, b = st.columns(2)
    with a:
        st.markdown(
            f"**Location** {farm.district}, {farm.province}  \n"
            f"**Area** {farm.area_acres:g} acres  \n"
            f"**Soil** {catalog.soil_label(farm.soil_type)}"
        )
    with b:
        st.markdown(
            f"**Crop** {analysis.crop.name}  \n"
            f"**Water** {farm.water_availability.title()} · "
            f"{farm.irrigation_method.title()}  \n"
            f"**Sowing** {farm.sowing_date:%d %b %Y}"
        )
    st.markdown(
        f'<span class="ap-pill">Estimated yield {fin.estimated_yield:,.0f} '
        f'{analysis.crop.yield_unit}</span>'
        f'<span class="ap-pill">Revenue {fmt_pkr(fin.estimated_revenue)}</span>'
        f'<span class="ap-pill">Cost {fmt_pkr(fin.total_cost)}</span>',
        unsafe_allow_html=True,
    )
    if fin.budget_gap < 0:
        st.warning(
            f"Estimated cost exceeds your budget by {fmt_pkr(abs(fin.budget_gap))}. "
            f"At {fmt_pkr(fin.cost_per_acre)} per acre, your budget covers about "
            f"{farm.budget_pkr / max(fin.cost_per_acre, 1):.1f} acres."
        )
    else:
        st.success(f"Budget covers the estimated cost with {fmt_pkr(fin.budget_gap)} to spare.")
    components.estimate_caption()

st.markdown("---")

# --- explanation + risks ------------------------------------------------------
left, right = st.columns([1.4, 1], gap="medium")
with left:
    st.markdown("#### Why this result")
    st.markdown(analysis.ai_explanation or "")

    def _retry() -> None:
        from agripilot.services import llm
        with st.spinner("Asking the AI model again…"):
            text, steps, source = llm.explain(analysis)
        analysis.ai_explanation, analysis.ai_next_steps, analysis.ai_source = text, steps, source
        st.rerun()

    components.ai_source_note(analysis, on_retry=_retry)

    if analysis.ai_next_steps:
        st.markdown("#### Next steps")
        for step in analysis.ai_next_steps:
            st.markdown(f"- {step}")

with right:
    st.markdown("#### Climate risk")
    if analysis.climate_risks:
        for risk in analysis.climate_risks:
            components.risk_card(risk)
    else:
        st.success("No significant climate risks identified for this crop and season.")

    st.markdown("#### Crop health")
    health = st.session_state.get("crop_health")
    if health:
        st.markdown(
            f"**{health.get('condition', 'Assessed')}** · "
            f"{health.get('severity', 'unknown').title()} severity"
        )
    else:
        st.caption("Not assessed. Upload a leaf photo on the Crop Health page.")

st.markdown("---")

# --- quick actions ------------------------------------------------------------
st.markdown("#### Quick actions")
actions = [
    ("Recommendation", "pages/3_Crop_Recommendation.py"),
    ("Compare crops", "pages/4_Crop_Comparison.py"),
    ("Irrigation", "pages/5_Irrigation.py"),
    ("Climate risk", "pages/6_Climate_Risk.py"),
    ("Financials", "pages/7_Financials.py"),
    ("What-If", "pages/8_What_If_Simulator.py"),
]
cols = st.columns(len(actions), gap="small")
for col, (label, page) in zip(cols, actions):
    with col:
        if st.button(label, use_container_width=True, key=f"qa_{label}"):
            st.switch_page(page)

# --- recent analyses ----------------------------------------------------------
rows = db.recent(5)
if rows:
    st.markdown("#### Recent analyses")
    for row in rows:
        c1, c2, c3, c4 = st.columns([2.4, 1.6, 1.4, 1], gap="small")
        c1.markdown(f"**{row['farm_name']}**" + (" · demo" if row["is_demo"] else ""))
        c2.caption(f"{row['crop_name']} · {row['district'] or '—'}")
        c3.caption(f"{row['decision_score']:.0f}/100 · {row['decision_label']}")
        if c4.button("Load", key=f"load_{row['id']}", use_container_width=True):
            loaded = db.get(row["id"])
            if loaded:
                state.set_analysis(loaded)
                st.rerun()
            else:
                st.error("That saved analysis could not be loaded.")

components.disclaimer()
