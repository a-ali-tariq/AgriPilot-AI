"""Page config, palette and CSS injection (PRD §11: clean, no neon, no animation)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from agripilot.config import DISCLAIMER

ASSETS = Path(__file__).parent.parent / "assets"
LOGO = ASSETS / "logo.png"      # full lockup: symbol, wordmark, tagline
MARK = ASSETS / "mark.png"      # symbol only, for the tab icon and sidebar

PRIMARY = "#2E7D32"
PRIMARY_DARK = "#1B5E20"
ACCENT = "#8D6E63"
BG = "#FAFAF7"
SURFACE = "#FFFFFF"
BORDER = "#E3E8DF"
TEXT = "#1F2A1F"
MUTED = "#5F6B5F"

SEVERITY_COLORS = {
    "low": "#2E7D32", "medium": "#E58A00", "high": "#C62828", "critical": "#8E0000",
}
SCORE_COLORS = {"good": "#2E7D32", "caution": "#E58A00", "poor": "#C62828"}

CSS = f"""
<style>
  .block-container {{ padding-top: 2.2rem; max-width: 1180px; }}
  h1, h2, h3 {{ color: {TEXT}; letter-spacing: -0.01em; }}

  .ap-card {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
    padding: 1rem 1.1rem; height: 100%;
  }}
  .ap-card-label {{
    font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em;
    color: {MUTED}; margin-bottom: 0.35rem;
  }}
  .ap-card-value {{ font-size: 1.55rem; font-weight: 650; color: {TEXT}; line-height: 1.2; }}
  .ap-card-sub {{ font-size: 0.82rem; color: {MUTED}; margin-top: 0.3rem; }}

  .ap-badge {{
    display: inline-block; padding: 0.18rem 0.6rem; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; color: #fff;
  }}
  .ap-pill {{
    display: inline-block; padding: 0.2rem 0.6rem; border-radius: 6px;
    background: #F1F5EE; border: 1px solid {BORDER}; color: {MUTED};
    font-size: 0.8rem; margin-right: 0.35rem;
  }}

  .ap-risk {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-left: 4px solid {MUTED};
    border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.7rem;
  }}
  .ap-risk h4 {{ margin: 0 0 0.3rem 0; font-size: 1rem; }}
  .ap-risk p {{ margin: 0.25rem 0; font-size: 0.9rem; color: {TEXT}; }}
  .ap-risk .ap-action {{ color: {PRIMARY_DARK}; font-weight: 500; }}

  .ap-source {{
    font-size: 0.82rem; color: {MUTED}; background: #F1F5EE;
    border: 1px solid {BORDER}; border-radius: 8px; padding: 0.4rem 0.7rem;
    margin-bottom: 0.8rem;
  }}
  .ap-demo {{
    background: #FFF6E5; border: 1px solid #F0D9A8; color: #7A5200;
    border-radius: 8px; padding: 0.5rem 0.8rem; font-size: 0.85rem;
    font-weight: 600; margin-bottom: 0.8rem;
  }}
  .ap-disclaimer {{
    font-size: 0.76rem; color: {MUTED}; line-height: 1.45;
    border-top: 1px solid {BORDER}; padding-top: 0.8rem; margin-top: 2.2rem;
  }}
  .ap-hero {{
    background: linear-gradient(135deg, #EDF4EA 0%, #F7FAF5 100%);
    border: 1px solid {BORDER}; border-radius: 16px; padding: 2.2rem 2rem;
    margin-bottom: 1.4rem;
  }}
  .ap-hero h1 {{ margin: 0 0 0.4rem 0; font-size: 2.4rem; }}
  .ap-hero p {{ margin: 0; color: {MUTED}; font-size: 1.05rem; }}

  [data-testid="stMetricValue"] {{ font-size: 1.5rem; }}
  @media (max-width: 640px) {{
    .ap-card-value {{ font-size: 1.25rem; }}
    .ap-hero h1 {{ font-size: 1.7rem; }}
    .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
  }}
</style>
"""


def setup(page_title: str, icon: str = "🌾", layout: str = "wide") -> None:
    """Call once at the top of every page, before any other Streamlit call.

    Falls back to the emoji icon if the logo files are missing, so a checkout
    without assets/ still runs.
    """
    st.set_page_config(
        page_title=f"{page_title} · AgriPilot AI",
        page_icon=str(MARK) if MARK.exists() else icon,
        layout=layout, initial_sidebar_state="expanded",
    )
    if LOGO.exists():
        st.logo(str(LOGO), icon_image=str(MARK) if MARK.exists() else None, size="large")
    st.markdown(CSS, unsafe_allow_html=True)


def score_color(score: float) -> str:
    if score >= 70:
        return SCORE_COLORS["good"]
    if score >= 45:
        return SCORE_COLORS["caution"]
    return SCORE_COLORS["poor"]
