"""Crop Health Image Analysis (FR-09, PRD §5.8)."""
from __future__ import annotations

import streamlit as st

from agripilot import state
from agripilot.config import get_secret
from agripilot.services import vision
from agripilot.services.vision import ImageValidationError
from ui import components, theme

theme.setup("Crop Health", icon="🩺")
state.init_state()
components.sidebar_summary()

st.title("Crop health check")
st.caption(
    "Upload a clear, close photo of an affected leaf or plant in daylight. "
    "This is a preliminary visual check, not a diagnosis."
)

uploaded = st.file_uploader(
    "Crop or leaf photo", type=["jpg", "jpeg", "png", "webp"],
    help=f"JPG, PNG or WEBP, up to {vision.MAX_BYTES // 1024 // 1024} MB",
)

if uploaded is not None:
    data = uploaded.getvalue()
    try:
        detected_mime, (width, height) = vision.validate_image(data, uploaded.type)
    except ImageValidationError as exc:
        st.error(str(exc))
        st.stop()

    left, right = st.columns([1, 1.4], gap="medium")
    with left:
        st.image(data, caption=f"{uploaded.name} · {width}x{height}", use_container_width=True)
        assess = st.button("Assess this image", type="primary", use_container_width=True)
    with right:
        if assess:
            try:
                with st.spinner("Looking at the image…"):
                    result = vision.assess_image(data, detected_mime)
                st.session_state["crop_health"] = result
            except Exception as exc:
                st.error(
                    "The image could not be assessed. Please try again. "
                    f"({type(exc).__name__})"
                )
                st.session_state["crop_health"] = None

        result = st.session_state.get("crop_health")
        if result:
            if not result.get("available"):
                st.warning(f"**{result['condition']}**: {result.get('reason', '')}")
            else:
                st.markdown(f"### {result['condition']}")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Confidence**")
                    st.progress(result["confidence"], text=f"{result['confidence']:.0%}")
                with c2:
                    severity = result.get("severity", "unknown")
                    color = {
                        "none": theme.SEVERITY_COLORS["low"],
                        "mild": theme.SEVERITY_COLORS["low"],
                        "moderate": theme.SEVERITY_COLORS["medium"],
                        "severe": theme.SEVERITY_COLORS["high"],
                    }.get(severity, theme.MUTED)
                    st.markdown(
                        f"**Possible severity**<br>"
                        f'<span class="ap-badge" style="background:{color}">'
                        f"{severity.upper()}</span>",
                        unsafe_allow_html=True,
                    )
                if result.get("symptoms"):
                    st.markdown("**Visible symptoms**")
                    for symptom in result["symptoms"]:
                        st.markdown(f"- {symptom}")

            if result.get("next_steps"):
                st.markdown("**Suggested next steps**")
                for step in result["next_steps"]:
                    st.markdown(f"- {step}")

            if st.button("Assess again"):
                st.session_state["crop_health"] = None
                st.rerun()

components.crop_health_disclaimer()

if not get_secret("LLM_API_KEY"):
    st.info(
        "Image assessment needs a vision model API key. Without one, AgriPilot AI will not "
        "guess at a condition, because a made-up diagnosis is worse than none. Every other part of "
        "the app works without it."
    )

components.disclaimer()
