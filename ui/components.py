"""Small presentation components shared across pages."""
from __future__ import annotations

from typing import Optional

import streamlit as st

from agripilot.config import CROP_HEALTH_DISCLAIMER, DISCLAIMER
from agripilot.models import Analysis, ClimateRisk, WeatherSummary
from agripilot.services import weather as weather_service

from .theme import BORDER, MUTED, SEVERITY_COLORS, score_color


def scorecard(label: str, value: str, sub: str = "", color: Optional[str] = None) -> None:
    value_style = f' style="color:{color}"' if color else ""
    st.markdown(
        f'<div class="ap-card"><div class="ap-card-label">{label}</div>'
        f'<div class="ap-card-value"{value_style}>{value}</div>'
        + (f'<div class="ap-card-sub">{sub}</div>' if sub else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def score_card(label: str, score: float, sub: str = "") -> None:
    scorecard(label, f"{score:.0f}<span style='font-size:0.9rem;color:#5F6B5F'> / 100</span>",
              sub, color=score_color(score))


def risk_badge(severity: str) -> str:
    color = SEVERITY_COLORS.get(severity, MUTED)
    return f'<span class="ap-badge" style="background:{color}">{severity.upper()}</span>'


def risk_card(risk: ClimateRisk) -> None:
    color = SEVERITY_COLORS.get(risk.severity, MUTED)
    st.markdown(
        f'<div class="ap-risk" style="border-left-color:{color}">'
        f'<h4>{risk.name} &nbsp;{risk_badge(risk.severity)}'
        f'<span style="font-size:0.78rem;color:{MUTED};font-weight:400"> &nbsp;· rule confidence '
        f'{risk.probability:.0%}</span></h4>'
        f'<p><strong>Possible impact:</strong> {risk.impact}</p>'
        f'<p class="ap-action"><strong>Suggested action:</strong> {risk.action}</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def source_banner(weather: WeatherSummary) -> None:
    st.markdown(
        f'<div class="ap-source">{weather_service.source_label(weather)}</div>',
        unsafe_allow_html=True,
    )


def demo_banner(analysis: Optional[Analysis] = None) -> None:
    farm = analysis.farm if analysis else st.session_state.get("farm")
    if farm is not None and getattr(farm, "is_demo", False):
        st.markdown(
            '<div class="ap-demo">DEMO FARM — sample data from the project brief, '
            'not a real farm.</div>',
            unsafe_allow_html=True,
        )


def ai_source_note(analysis: Analysis, on_retry=None) -> None:
    """Say plainly whether the explanation came from the model or the engine."""
    if analysis.ai_source == "llm":
        st.caption("Explanation written by the AI model from the calculated results above.")
        return
    col_a, col_b = st.columns([4, 1])
    with col_a:
        st.caption(
            "AI explanation unavailable — this summary is generated directly from the "
            "calculation engine. All numbers are identical either way."
        )
    if on_retry is not None:
        with col_b:
            if st.button("Retry AI", use_container_width=True):
                on_retry()


def estimate_caption() -> None:
    st.caption("All financial figures are estimates, not guarantees.")


def empty_state(message: str, button_label: str, page: str) -> None:
    st.info(message)
    if st.button(button_label, type="primary"):
        st.switch_page(page)


def disclaimer() -> None:
    st.markdown(f'<div class="ap-disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)


def crop_health_disclaimer() -> None:
    st.warning(CROP_HEALTH_DISCLAIMER)


def sidebar_summary() -> None:
    """Compact farm summary in the sidebar so context follows the user across pages."""
    analysis = st.session_state.get("analysis")
    with st.sidebar:
        st.markdown("### AgriPilot AI")
        if analysis is None:
            st.caption("No analysis yet. Start from Farm Input.")
            return
        farm = analysis.farm
        st.markdown(f"**{farm.name}**")
        st.caption(
            f"{farm.district}, {farm.province}  \n"
            f"{farm.area_acres:g} acres · {analysis.crop.name}  \n"
            f"Sowing {farm.sowing_date:%d %b %Y}"
        )
        st.metric("Farm Decision Score", f"{analysis.decision_score:.0f}/100",
                  analysis.decision_label)
        st.caption(
            "Weather: live" if analysis.weather.source == "live" else "Weather: demo data"
        )
