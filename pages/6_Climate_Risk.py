"""Climate Risk — FR-06, PRD §5.5."""
from __future__ import annotations

import streamlit as st

from agripilot import state
from agripilot.engine import climate as climate_engine
from ui import components, theme

theme.setup("Climate Risk", icon="🌦️")
state.init_state()
components.sidebar_summary()

st.title("Climate risk")
analysis = state.require_analysis("climate risk")
components.demo_banner(analysis)
components.source_banner(analysis.weather)

weather = analysis.weather
severity = climate_engine.overall_severity(analysis.climate_risks)

c1, c2, c3, c4 = st.columns(4, gap="small")
with c1:
    components.scorecard(
        "Overall risk", severity.title(), f"{len(analysis.climate_risks)} identified",
        color=theme.SEVERITY_COLORS.get(severity),
    )
with c2:
    components.scorecard("Average temperature", f"{weather.avg_temp:.0f}°C",
                         f"Crop range {analysis.crop.temp_range_c[0]:.0f}–"
                         f"{analysis.crop.temp_range_c[1]:.0f}°C")
with c3:
    components.scorecard("Temperature range", f"{weather.min_temp:.0f}–{weather.max_temp:.0f}°C",
                         "Recent minimum and maximum")
with c4:
    components.scorecard("Rainfall", f"{weather.rainfall_mm_30d:.0f} mm",
                         f"Last 30 days · {weather.forecast_rain_mm_7d:.0f} mm forecast (7 days)")

st.markdown("")

if analysis.climate_risks:
    st.markdown("#### Identified risks")
    st.caption(
        "Each risk comes from a rule checked against your farm, crop and weather data. "
        "Confidence values are fixed rule confidences, not model predictions."
    )
    for risk in analysis.climate_risks:
        components.risk_card(risk)
else:
    st.success(
        "No significant climate risks detected for this crop, location and season based on "
        "the available weather data. Conditions can still change — check local forecasts "
        "before sowing."
    )

with st.expander("Weather data used"):
    st.markdown(
        f"- Average temperature: **{weather.avg_temp:.1f}°C**\n"
        f"- Maximum temperature: **{weather.max_temp:.1f}°C**\n"
        f"- Minimum temperature: **{weather.min_temp:.1f}°C**\n"
        f"- Humidity: **{weather.humidity_pct:.0f}%**\n"
        f"- Rainfall, last 30 days: **{weather.rainfall_mm_30d:.0f} mm**\n"
        f"- Forecast rainfall, next 7 days: **{weather.forecast_rain_mm_7d:.0f} mm**\n"
        f"- Source: **{'live (OpenWeatherMap)' if weather.source == 'live' else 'demo data'}**"
    )

components.disclaimer()
