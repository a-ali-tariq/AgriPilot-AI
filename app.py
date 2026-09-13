"""AgriPilot AI — landing page and Streamlit entry point."""
from __future__ import annotations

import streamlit as st

from agripilot import state
from ui import components, theme

theme.setup("Home", icon="🌾")
state.init_state()

hero_text, hero_logo = st.columns([2.2, 1], gap="medium")
with hero_text:
    st.markdown(
        '<div class="ap-hero">'
        "<h1>AgriPilot AI</h1>"
        "<p>Smarter Decisions, Sustainable Agriculture.</p>"
        '<p style="font-size:0.92rem;margin-top:0.5rem">'
        "Intelligent Farm Decision &amp; Optimization Engine</p>"
        "</div>",
        unsafe_allow_html=True,
    )
with hero_logo:
    if theme.LOGO.exists():
        st.image(str(theme.LOGO), use_container_width=True)

st.markdown(
    "Deciding what to grow means weighing soil, water, weather, cost and price all at once. "
    "AgriPilot AI brings those together into one clear recommendation — with the reasoning "
    "shown, not hidden."
)

left, mid, right = st.columns(3, gap="medium")
for col, (step, title, body) in zip(
    (left, mid, right),
    [
        ("1", "Farm Data", "Tell us your location, land, soil, water, crop, sowing date and budget."),
        ("2", "AI Analysis", "Suitability, irrigation, climate risk and financials, calculated and explained."),
        ("3", "Better Decision", "A Farm Decision Score, scenario testing and a report you can take with you."),
    ],
):
    with col:
        st.markdown(
            f'<div class="ap-card"><div class="ap-card-label">Step {step}</div>'
            f'<div class="ap-card-value" style="font-size:1.15rem">{title}</div>'
            f'<div class="ap-card-sub">{body}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("")
col_a, col_b = st.columns(2, gap="medium")
with col_a:
    if st.button("Start with my farm", type="primary", use_container_width=True):
        st.switch_page("pages/1_Farm_Input.py")
with col_b:
    if st.button("Try the Demo Farm", use_container_width=True):
        with st.spinner("Running the demo farm analysis…"):
            state.load_demo_farm()
        st.switch_page("pages/2_Dashboard.py")
st.caption(
    "Demo Farm: 10 acres of rice near Hyderabad, Sindh — limited water, PKR 500,000 budget."
)

st.markdown("---")
st.subheader("What it does")

features = [
    ("Crop recommendation", "Scores your planned crop on soil, season, water, climate and budget — and says why."),
    ("Crop comparison", "Put up to four crops side by side on water, cost, yield, profit and risk."),
    ("Irrigation plan", "Seasonal water requirement, irrigation frequency, stage-by-stage schedule and savings tips."),
    ("Climate risk", "Heat stress, drought, heavy rain and water shortage, each with a practical action."),
    ("Financial feasibility", "Cost, revenue, profit, ROI and the gap against your budget."),
    ("What-If simulator", "Move water, temperature, costs and price, and watch the outcome change."),
    ("Crop health check", "Upload a leaf photo for a preliminary, clearly-labelled assessment."),
    ("PDF report", "One professional document covering the whole analysis."),
]
for row in range(0, len(features), 4):
    cols = st.columns(4, gap="small")
    for col, (title, body) in zip(cols, features[row:row + 4]):
        with col:
            st.markdown(
                f'<div class="ap-card"><div class="ap-card-value" style="font-size:1rem">{title}</div>'
                f'<div class="ap-card-sub">{body}</div></div>',
                unsafe_allow_html=True,
            )

st.markdown("")
st.caption(
    "Built for Pakistan — Punjab, Sindh, Khyber Pakhtunkhwa and Balochistan, in acres and PKR."
)

st.markdown("---")
about, contact = st.columns([3, 1], gap="medium")
with about:
    st.markdown("**Built by Team AgriNex** — get in touch about the project or the data.")
with contact:
    if st.button("Meet the team", use_container_width=True):
        st.switch_page("pages/11_Team.py")

components.sidebar_summary()
components.disclaimer()
