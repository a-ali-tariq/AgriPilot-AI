"""Crop Recommendation — FR-02, FR-03, PRD §5.2."""
from __future__ import annotations

import streamlit as st

from agripilot import state
from ui import charts, components, theme

theme.setup("Crop Recommendation", icon="🌱")
state.init_state()
components.sidebar_summary()

st.title("Crop recommendation")
analysis = state.require_analysis("the recommendation")
components.demo_banner(analysis)
components.source_banner(analysis.weather)

suit = analysis.suitability

left, right = st.columns([1, 1.3], gap="medium")
with left:
    components.score_card(
        f"{analysis.crop.name} suitability", suit.score,
        f"Farm Decision Score {analysis.decision_score:.0f}/100 · {analysis.decision_label}",
    )
    st.markdown("")
    st.markdown(
        f"**{analysis.crop.name}** ({analysis.crop.name_ur}) · "
        f"{', '.join(analysis.crop.seasons)} season  \n"
        f"{analysis.crop.duration_days} days to harvest · "
        f"about {analysis.crop.water_need_mm:.0f} mm of water"
    )
    st.caption(analysis.crop.notes)
with right:
    st.plotly_chart(charts.subscore_bar(suit), use_container_width=True,
                    config={"displayModeBar": False})

st.markdown("#### Why this recommendation")
st.markdown(analysis.ai_explanation or "")


def _retry() -> None:
    from agripilot.services import llm
    with st.spinner("Asking the AI model again…"):
        text, steps, source = llm.explain(analysis)
    analysis.ai_explanation, analysis.ai_next_steps, analysis.ai_source = text, steps, source
    st.rerun()


components.ai_source_note(analysis, on_retry=_retry)

with st.expander("The calculated reasons behind each score", expanded=False):
    for reason in suit.reasons:
        st.markdown(f"- {reason}")
    st.caption(
        "These come straight from the calculation engine and are shown whether or not "
        "the AI model is available."
    )

if suit.warnings:
    st.markdown("#### Warnings")
    for warning in suit.warnings:
        st.warning(warning)

if analysis.ai_next_steps:
    st.markdown("#### Next steps")
    for step in analysis.ai_next_steps:
        st.markdown(f"- {step}")

st.markdown("---")
st.markdown("#### Other crops worth considering")
st.caption(
    f"Scored against the same farm conditions. Crops commonly grown in {analysis.farm.province}."
)

for alt in analysis.alternatives:
    c1, c2, c3 = st.columns([2, 1, 3.5], gap="small")
    c1.markdown(f"**{alt.crop_name}**")
    c2.markdown(
        f"<span style='color:{theme.score_color(alt.score)};font-weight:650'>"
        f"{alt.score:.0f}/100</span>", unsafe_allow_html=True,
    )
    best_factor = max(alt.subscores().items(), key=lambda kv: kv[1])
    worst_factor = min(alt.subscores().items(), key=lambda kv: kv[1])
    c3.caption(
        f"Strongest on {best_factor[0].lower()} ({best_factor[1]:.0f}), "
        f"weakest on {worst_factor[0].lower()} ({worst_factor[1]:.0f})."
    )

st.markdown("")
if st.button("Compare these crops side by side", type="primary"):
    st.session_state["comparison_preselect"] = (
        [analysis.crop.id] + [a.crop_id for a in analysis.alternatives[:2]]
    )
    st.switch_page("pages/4_Crop_Comparison.py")

components.disclaimer()
