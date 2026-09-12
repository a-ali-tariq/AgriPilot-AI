"""Farm Report — FR-10, PRD §5.10."""
from __future__ import annotations

from datetime import date

import streamlit as st

from agripilot import state
from agripilot.services.report import build_pdf
from ui import components, theme

theme.setup("Report", icon="📄")
state.init_state()
components.sidebar_summary()

st.title("Farm report")
analysis = state.require_analysis("the report")
components.demo_banner(analysis)

st.caption(
    "A single PDF covering the whole analysis — something you can print, share with a "
    "lender, or take to your extension officer."
)

comparison = st.session_state.get("comparison")
scenario_diff = st.session_state.get("scenario_diff")
crop_health = st.session_state.get("crop_health")

st.markdown("#### What goes in")

always_in = [
    ("Farm information", f"{analysis.farm.name}, {analysis.farm.district}, "
                         f"{analysis.farm.area_acres:g} acres"),
    ("Crop recommendation", f"{analysis.crop.name} · suitability "
                            f"{analysis.suitability.score:.0f}/100"),
    ("Irrigation analysis", f"{analysis.water.gross_requirement_mm:,.0f} mm · "
                            f"{analysis.water.stress_level} stress"),
    ("Climate risk", f"{len(analysis.climate_risks)} risk(s) identified"),
    ("Financial analysis", f"Estimated profit PKR {analysis.finance.estimated_profit:,.0f}"),
    ("Feasibility score and recommendation",
     f"{analysis.decision_score:.0f}/100 · {analysis.decision_label}"),
    ("Action plan and disclaimer", f"{len(analysis.ai_next_steps or [])} next steps"),
]
for title, detail in always_in:
    st.markdown(f"- **{title}** — {detail}")

st.markdown("#### Optional sections")
col_a, col_b, col_c = st.columns(3)
with col_a:
    include_comparison = st.checkbox(
        "Crop comparison", value=bool(comparison), disabled=not comparison,
        help="Visit the Crop Comparison page first" if not comparison else None,
    )
with col_b:
    include_scenario = st.checkbox(
        "What-If simulation", value=bool(scenario_diff), disabled=not scenario_diff,
        help="Run a scenario in the simulator first" if not scenario_diff else None,
    )
with col_c:
    include_health = st.checkbox(
        "Crop health assessment",
        value=bool(crop_health and crop_health.get("available")),
        disabled=not (crop_health and crop_health.get("available")),
        help="Assess an image on the Crop Health page first"
        if not (crop_health and crop_health.get("available")) else None,
    )

if not comparison or not scenario_diff:
    missing = [
        name for name, present in
        [("Crop Comparison", comparison), ("What-If Simulator", scenario_diff)] if not present
    ]
    st.info(
        f"Visit the {' and '.join(missing)} page{'s' if len(missing) > 1 else ''} first to "
        "include those sections in the report."
    )

st.markdown("")
if st.button("Generate PDF", type="primary", use_container_width=True):
    try:
        with st.spinner("Building your report…"):
            pdf = build_pdf(
                analysis,
                comparison=comparison if include_comparison else None,
                scenario_diff=scenario_diff if include_scenario else None,
                crop_health=crop_health if include_health else None,
            )
        st.session_state["report_pdf"] = pdf
        st.success(f"Report ready — {len(pdf) / 1024:,.0f} KB.")
    except Exception as exc:
        st.error(
            "The report could not be generated. Please try again. "
            f"({type(exc).__name__})"
        )

pdf = st.session_state.get("report_pdf")
if pdf:
    safe_name = "".join(
        ch if ch.isalnum() or ch in "-_" else "_" for ch in analysis.farm.name
    ).strip("_") or "farm"
    st.download_button(
        "Download PDF", data=pdf,
        file_name=f"AgriPilot_{safe_name}_{date.today():%Y-%m-%d}.pdf",
        mime="application/pdf", use_container_width=True,
    )

components.disclaimer()
