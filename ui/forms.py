"""Farm input form and input validation (FR-01, PRD §5.1, §9)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import streamlit as st

from agripilot import catalog
from agripilot.engine import finance as finance_engine
from agripilot.engine.units import hectares_to_acres, kanal_to_acres
from agripilot.models import CostInputs, Farm

MAX_NAME_LEN = 60
MAX_AREA_ACRES = 10_000.0
SOWING_WINDOW_DAYS = 365

SOIL_OPTIONS = ["loamy", "clay_loam", "clay", "sandy_loam", "sandy", "silty"]
WATER_OPTIONS = ["abundant", "adequate", "limited", "scarce"]
IRRIGATION_OPTIONS = ["flood", "furrow", "sprinkler", "drip", "tubewell", "rainfed"]
AREA_UNITS = {"Acres": 1.0, "Kanal": None, "Hectares": None}

WATER_HELP = {
    "abundant": "Canal plus tubewell, water rarely a constraint",
    "adequate": "Enough water for a normal season",
    "limited": "Restricted canal turns or costly pumping",
    "scarce": "Serious shortage, mostly rainfed",
}


def _title(value: str) -> str:
    return value.replace("_", " ").title()


def validate(farm: Farm, costs: CostInputs) -> list[str]:
    """Return a list of human-readable problems. Empty list means valid."""
    errors: list[str] = []

    if not farm.name.strip():
        errors.append("Farm name is required.")
    elif len(farm.name) > MAX_NAME_LEN:
        errors.append(f"Farm name must be {MAX_NAME_LEN} characters or fewer.")

    if farm.area_acres <= 0:
        errors.append("Farm area must be greater than 0.")
    elif farm.area_acres > MAX_AREA_ACRES:
        errors.append(f"Farm area above {MAX_AREA_ACRES:,.0f} acres is outside the supported range.")

    if farm.budget_pkr < 0:
        errors.append("Budget cannot be negative.")

    if farm.district not in catalog.districts(farm.province):
        errors.append(f"{farm.district} is not a district of {farm.province}.")

    delta = abs((farm.sowing_date - date.today()).days)
    if delta > SOWING_WINDOW_DAYS:
        errors.append("Sowing date must be within one year of today.")

    negative = [k for k, v in costs.breakdown().items() if v < 0]
    if negative:
        errors.append(f"Cost cannot be negative: {', '.join(negative)}.")
    if costs.expected_price_per_unit < 0:
        errors.append("Expected price cannot be negative.")

    try:
        catalog.crop(farm.planned_crop)
    except KeyError:
        errors.append(f"Unknown crop '{farm.planned_crop}'.")

    return errors


def farm_form(prefill: Optional[Farm] = None) -> tuple[Farm, CostInputs, bool]:
    """Render the farm input widgets. Returns (farm, costs, submitted)."""
    base = prefill or st.session_state.get("farm")

    st.subheader("1. Where is your farm?")
    col1, col2, col3 = st.columns([2, 1.4, 1.4], gap="small")
    with col1:
        name = st.text_input(
            "Farm name", value=base.name if base else "", max_chars=MAX_NAME_LEN,
            placeholder="e.g. Chak 42 farm",
        )
    provinces = catalog.provinces()
    with col2:
        province = st.selectbox(
            "Province", provinces,
            index=provinces.index(base.province) if base and base.province in provinces else 0,
        )
    districts = catalog.districts(province)
    with col3:
        district = st.selectbox(
            "District", districts,
            index=districts.index(base.district) if base and base.district in districts else 0,
        )

    st.subheader("2. Land and water")
    col1, col2, col3 = st.columns(3, gap="small")
    with col1:
        unit = st.selectbox("Area unit", list(AREA_UNITS.keys()))
        raw_area = st.number_input(
            f"Farm area ({unit.lower()})", min_value=0.0, step=1.0,
            value=float(base.area_acres) if base and unit == "Acres" else 10.0,
            help="1 acre = 8 kanal = 0.405 hectares",
        )
        area_acres = {
            "Acres": raw_area,
            "Kanal": kanal_to_acres(raw_area),
            "Hectares": hectares_to_acres(raw_area),
        }[unit]
        if unit != "Acres":
            st.caption(f"= {area_acres:,.2f} acres")
    with col2:
        soil = st.selectbox(
            "Soil type", SOIL_OPTIONS,
            index=SOIL_OPTIONS.index(base.soil_type) if base and base.soil_type in SOIL_OPTIONS else 0,
            format_func=catalog.soil_label,
        )
        st.caption(catalog.soils().get(soil, {}).get("note", ""))
    with col3:
        water = st.selectbox(
            "Water availability", WATER_OPTIONS,
            index=WATER_OPTIONS.index(base.water_availability)
            if base and base.water_availability in WATER_OPTIONS else 1,
            format_func=_title,
        )
        st.caption(WATER_HELP[water])

    st.subheader("3. Crop and season")
    crops = list(catalog.crops().values())
    crops.sort(key=lambda c: (c.seasons[0] if c.seasons else "", c.name))
    crop_ids = [c.id for c in crops]
    labels = {c.id: f"{c.name} · {', '.join(c.seasons)}" for c in crops}

    col1, col2, col3 = st.columns(3, gap="small")
    with col1:
        irrigation = st.selectbox(
            "Irrigation method", IRRIGATION_OPTIONS,
            index=IRRIGATION_OPTIONS.index(base.irrigation_method)
            if base and base.irrigation_method in IRRIGATION_OPTIONS else 0,
            format_func=_title,
        )
    with col2:
        crop_id = st.selectbox(
            "Planned crop", crop_ids,
            index=crop_ids.index(base.planned_crop)
            if base and base.planned_crop in crop_ids else 0,
            format_func=lambda cid: labels[cid],
        )
    with col3:
        sowing = st.date_input(
            "Sowing date",
            value=base.sowing_date if base else date.today(),
            min_value=date.today() - timedelta(days=SOWING_WINDOW_DAYS),
            max_value=date.today() + timedelta(days=SOWING_WINDOW_DAYS),
        )

    crop = catalog.crop(crop_id)
    st.caption(
        f"**{crop.name}** — recommended sowing {crop.sowing_window[0]} to "
        f"{crop.sowing_window[1]}, about {crop.duration_days} days to harvest, "
        f"roughly {crop.water_need_mm:.0f} mm of water. {crop.notes}"
    )

    st.subheader("4. Budget and costs")
    budget = st.number_input(
        "Available budget (PKR)", min_value=0.0, step=10_000.0,
        value=float(base.budget_pkr) if base else 500_000.0,
        help="Total money available for this crop across the whole farm.",
    )

    defaults = finance_engine.default_costs_for(crop)
    typical_total = defaults.per_acre_total() * max(area_acres, 0)
    with st.expander(
        f"Cost details (optional) — typical total for {area_acres:,.1f} acres is "
        f"about PKR {typical_total:,.0f}"
    ):
        st.caption(
            "Values are per acre and prefilled with typical figures for this crop. "
            "Edit any of them to match your own costs."
        )
        c1, c2, c3, c4 = st.columns(4, gap="small")
        with c1:
            seed = st.number_input("Seed / acre", min_value=0.0, value=defaults.seed, step=500.0)
            fertilizer = st.number_input("Fertilizer / acre", min_value=0.0, value=defaults.fertilizer, step=500.0)
        with c2:
            labor = st.number_input("Labor / acre", min_value=0.0, value=defaults.labor, step=500.0)
            irrigation_cost = st.number_input("Irrigation / acre", min_value=0.0, value=defaults.irrigation, step=500.0)
        with c3:
            pesticide = st.number_input("Pesticide / acre", min_value=0.0, value=defaults.pesticide, step=500.0)
            machinery = st.number_input("Machinery / acre", min_value=0.0, value=defaults.machinery, step=500.0)
        with c4:
            other = st.number_input("Other / acre", min_value=0.0, value=defaults.other, step=500.0)
            price = st.number_input(
                f"Expected price per {crop.yield_unit}", min_value=0.0,
                value=defaults.expected_price_per_unit, step=100.0,
                help=f"PKR you expect to receive per {crop.yield_unit} at harvest.",
            )

    costs = CostInputs(
        seed=seed, fertilizer=fertilizer, labor=labor, irrigation=irrigation_cost,
        pesticide=pesticide, machinery=machinery, other=other,
        expected_price_per_unit=price,
    )

    coords = catalog.district_coords(province, district) or (None, None)
    farm = Farm(
        name=name.strip(), province=province, district=district,
        area_acres=float(area_acres), soil_type=soil, water_availability=water,
        irrigation_method=irrigation, planned_crop=crop_id, sowing_date=sowing,
        budget_pkr=float(budget), lat=coords[0], lon=coords[1],
        # Editing the demo farm's name means it is no longer the demo farm.
        is_demo=bool(base.is_demo and name.strip() == base.name) if base else False,
    )

    st.markdown("")
    submitted = st.button(
        "Generate AI analysis", type="primary", use_container_width=True,
    )
    return farm, costs, submitted
