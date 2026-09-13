"""Crop Comparison (FR-04, PRD §5.3)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from agripilot import catalog, state
from agripilot.pipeline import compare_crops
from ui import charts, components, theme

theme.setup("Crop Comparison", icon="⚖️")
state.init_state()
components.sidebar_summary()

st.title("Compare crops")
analysis = state.require_analysis("crop comparison")
components.demo_banner(analysis)
components.source_banner(analysis.weather)

st.caption(
    "Every crop is costed with its own typical inputs and priced at its own typical market "
    "rate, then scored against your farm's soil, water, weather and sowing date."
)

available = catalog.crops_for_province(analysis.farm.province) or list(catalog.crops().values())
options = [c.id for c in available]
labels = {c.id: c.name for c in available}

default = st.session_state.pop("comparison_preselect", None) or (
    [analysis.crop.id] + [a.crop_id for a in analysis.alternatives[:2]]
)
default = [cid for cid in dict.fromkeys(default) if cid in options][:4]

selected = st.multiselect(
    "Crops to compare (up to 4)", options, default=default,
    format_func=lambda cid: labels[cid], max_selections=4,
)

if not selected:
    st.info("Select at least one crop to compare.")
    components.disclaimer()
    st.stop()

rows = compare_crops(analysis.farm, analysis.weather, selected)
st.session_state["comparison"] = rows

table = pd.DataFrame([{
    "Crop": r["crop"],
    "Season": r["season"].title(),
    "Suitability": r["suitability"],
    "Water (mm)": r["water_mm"],
    "Water stress": r["water_stress"].title(),
    "Est. cost (PKR)": r["cost"],
    f"Est. yield": f"{r['yield']:,.0f} {r['yield_unit']}",
    "Est. revenue (PKR)": r["revenue"],
    "Est. profit (PKR)": r["profit"],
    "ROI %": r["roi"],
    "Climate risk": r["risk"].title(),
} for r in rows])

st.dataframe(
    table.style.format({
        "Suitability": "{:.0f}", "Water (mm)": "{:,.0f}", "Est. cost (PKR)": "{:,.0f}",
        "Est. revenue (PKR)": "{:,.0f}", "Est. profit (PKR)": "{:,.0f}", "ROI %": "{:.0f}",
    }),
    use_container_width=True, hide_index=True,
)
components.estimate_caption()

left, right = st.columns(2, gap="medium")
with left:
    st.plotly_chart(
        charts.comparison_bars(rows, "profit", "Estimated profit by crop (PKR)", money=True),
        use_container_width=True, config={"displayModeBar": False},
    )
with right:
    st.plotly_chart(
        charts.comparison_bars(rows, "suitability", "Suitability score by crop"),
        use_container_width=True, config={"displayModeBar": False},
    )

best_profit = max(rows, key=lambda r: r["profit"])
best_fit = max(rows, key=lambda r: r["suitability"])
least_water = min(rows, key=lambda r: r["water_mm"])

st.markdown("#### What the comparison shows")
st.markdown(
    f"- **Highest estimated profit:** {best_profit['crop']} at "
    f"PKR {best_profit['profit']:,.0f} ({best_profit['roi']:.0f}% ROI)\n"
    f"- **Best fit for your farm:** {best_fit['crop']} at "
    f"{best_fit['suitability']:.0f}/100 suitability\n"
    f"- **Least water needed:** {least_water['crop']} at "
    f"{least_water['water_mm']:,.0f} mm for the season"
)
if best_profit["crop_id"] != best_fit["crop_id"]:
    st.info(
        f"The most profitable crop on paper ({best_profit['crop']}) is not the best fit for "
        f"your conditions ({best_fit['crop']}). Profit estimates assume the crop grows well, "
        "a poor fit makes that assumption weaker."
    )

components.disclaimer()
