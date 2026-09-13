"""Farm Input (FR-01, PRD §5.1)."""
from __future__ import annotations

import streamlit as st

from agripilot import db, state
from agripilot.pipeline import run_analysis
from ui import components, forms, theme

theme.setup("Farm Input", icon="🌾")
state.init_state()
components.sidebar_summary()

st.title("Your farm")
st.caption("Everything here stays in this session. Only the farm name is saved with an analysis.")

col_a, col_b = st.columns([3, 1])
with col_b:
    if st.button("Load Demo Farm", use_container_width=True,
                 help="Fill the form with the sample farm from the project brief"):
        state.prefill_from_demo()
        st.rerun()

components.demo_banner()

prefill = st.session_state.pop("prefill", None)
farm, costs, submitted = forms.farm_form(prefill)

if submitted:
    errors = forms.validate(farm, costs)
    if errors:
        for error in errors:
            st.error(error)
    else:
        try:
            with st.spinner("Analysing your farm…"):
                analysis = run_analysis(farm, costs, use_llm=True)
            state.set_analysis(analysis)
            db.save(analysis)
            st.success(
                f"Analysis ready. Farm Decision Score {analysis.decision_score:.0f}/100 "
                f"({analysis.decision_label})."
            )
            st.switch_page("pages/2_Dashboard.py")
        except Exception as exc:  # never show a raw traceback (PRD §10)
            st.error(
                "Something went wrong while analysing this farm. Please check your inputs "
                f"and try again. ({type(exc).__name__})"
            )

components.disclaimer()
