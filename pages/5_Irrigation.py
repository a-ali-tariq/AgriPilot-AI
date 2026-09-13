"""Irrigation Optimizer (FR-05, PRD §5.4)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from agripilot import catalog, state
from agripilot.models import IRRIGATION_EFFICIENCY
from ui import charts, components, theme

theme.setup("Irrigation", icon="💧")
state.init_state()
components.sidebar_summary()

st.title("Irrigation plan")
analysis = state.require_analysis("the irrigation plan")
components.demo_banner(analysis)
components.source_banner(analysis.weather)

water, farm, crop = analysis.water, analysis.farm, analysis.crop
efficiency = IRRIGATION_EFFICIENCY.get(farm.irrigation_method, 0.6)

c1, c2, c3, c4 = st.columns(4, gap="small")
with c1:
    components.scorecard(
        "Water to apply", f"{water.gross_requirement_mm:,.0f} mm",
        f"{water.seasonal_requirement_liters / 1e6:,.1f} million litres over "
        f"{farm.area_acres:g} acres",
    )
with c2:
    components.scorecard("Irrigation events", f"{water.irrigation_events}",
                         f"Across {crop.duration_days} days")
with c3:
    components.scorecard("Frequency", f"Every {water.frequency_days} days",
                         f"{farm.irrigation_method.title()} irrigation")
with c4:
    components.scorecard(
        "Water stress", water.stress_level.title(),
        f"Stress index {water.stress_score:.2f} of 1.00",
        color=theme.SEVERITY_COLORS.get(water.stress_level, theme.MUTED),
    )

st.markdown("")

stress_message = {
    "low": "Your water supply comfortably covers this crop's requirement.",
    "medium": "Your water supply is close to this crop's requirement. Timing matters.",
    "high": "Your water supply falls well short of this crop's requirement. Expect yield loss "
            "unless you improve efficiency or reduce the area.",
    "critical": "Your water supply cannot meet this crop's requirement. This is a crop-failure "
                "level shortfall, not a yield penalty.",
}[water.stress_level]
(st.success if water.stress_level == "low" else
 st.info if water.stress_level == "medium" else st.warning)(stress_message)

left, right = st.columns([1.3, 1], gap="medium")
with left:
    st.plotly_chart(charts.stage_water_bars(water), use_container_width=True,
                    config={"displayModeBar": False})
with right:
    st.markdown("#### How the requirement was calculated")
    st.markdown(
        f"- Crop requirement: **{crop.water_need_mm:,.0f} mm** for {crop.name.lower()}\n"
        f"- Soil adjustment ({catalog.soil_label(farm.soil_type)}): "
        f"x{catalog.soil_water_factor(farm.soil_type):.2f} → "
        f"**{water.seasonal_requirement_mm:,.0f} mm** needed in the root zone\n"
        f"- Effective rainfall: **−{water.effective_rainfall_mm:,.0f} mm**\n"
        f"- {farm.irrigation_method.title()} irrigation efficiency: "
        f"**{efficiency:.0%}** → **{water.gross_requirement_mm:,.0f} mm** must be applied"
    )
    st.caption(
        "Applied water is higher than the crop's need because part of every irrigation is "
        "lost to runoff, deep drainage and evaporation."
    )

st.markdown("#### Stage-by-stage schedule")
schedule = pd.DataFrame(water.stage_schedule)
schedule = schedule.rename(columns={
    "stage": "Growth stage", "days": "Days", "kc": "Crop coefficient (Kc)",
    "water_mm": "Water (mm)", "events": "Irrigations", "liters": "Litres",
})
st.dataframe(
    schedule.style.format({
        "Water (mm)": "{:,.0f}", "Litres": "{:,.0f}", "Crop coefficient (Kc)": "{:.2f}",
    }),
    use_container_width=True, hide_index=True,
)

st.markdown("#### Ways to use less water")
for tip in water.savings_tips:
    st.markdown(f"- {tip}")

with st.expander("What if I changed irrigation method?"):
    from dataclasses import replace

    from agripilot.engine import water as water_engine

    rows = []
    for method, eff in IRRIGATION_EFFICIENCY.items():
        if method == "rainfed":
            continue
        alt_farm = replace(farm, irrigation_method=method)
        alt = water_engine.compute(alt_farm, crop, analysis.weather)
        rows.append({
            "Method": method.title(),
            "Efficiency": f"{eff:.0%}",
            "Water to apply (mm)": round(alt.gross_requirement_mm),
            "Irrigations": alt.irrigation_events,
            "Water stress": alt.stress_level.title(),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Same crop, same weather, same soil. Only the irrigation method changes.")

components.disclaimer()
