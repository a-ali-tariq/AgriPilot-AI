"""Session-state helpers shared by every page."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import streamlit as st

from . import catalog, db
from .engine import finance
from .models import Analysis, CostInputs, Farm, Scenario

DEFAULTS = {
    "farm": None, "costs": None, "analysis": None, "comparison": None,
    "scenario": None, "scenario_analysis": None, "crop_health": None,
    "prefill": None, "assistant_history": [],
}


def init_state() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)


def has_analysis() -> bool:
    return st.session_state.get("analysis") is not None


def get_analysis() -> Optional[Analysis]:
    return st.session_state.get("analysis")


def set_analysis(analysis: Analysis) -> None:
    st.session_state["analysis"] = analysis
    st.session_state["farm"] = analysis.farm
    st.session_state["costs"] = analysis.costs
    # A new base analysis invalidates any scenario built on the old one.
    st.session_state["scenario_analysis"] = None


def require_analysis(page_name: str = "this page") -> Optional[Analysis]:
    """Render an empty state and stop the page if no analysis exists (PRD §11)."""
    analysis = get_analysis()
    if analysis is not None:
        return analysis

    st.info(
        f"**No farm analysis yet.** {page_name.capitalize()} needs your farm details first. "
        "Enter your farm, or load the demo farm to see how it works."
    )
    left, right = st.columns(2)
    with left:
        if st.button("Go to Farm Input", type="primary", use_container_width=True):
            st.switch_page("pages/1_Farm_Input.py")
    with right:
        if st.button("Load Demo Farm", use_container_width=True):
            load_demo_farm()
            st.rerun()
    st.stop()
    return None


def demo_farm() -> Farm:
    """Build the PRD §13 demo farm. Sowing date is this year's 15 July."""
    raw = catalog.demo_farm_raw()
    month, day = (int(p) for p in raw["sowing_date"].split("-"))
    return Farm(
        name=raw["name"], province=raw["province"], district=raw["district"],
        area_acres=float(raw["area_acres"]), soil_type=raw["soil_type"],
        water_availability=raw["water_availability"],
        irrigation_method=raw["irrigation_method"], planned_crop=raw["planned_crop"],
        sowing_date=date(date.today().year, month, day),
        budget_pkr=float(raw["budget_pkr"]),
        lat=raw.get("lat"), lon=raw.get("lon"), is_demo=True,
    )


def load_demo_farm(run: bool = True) -> Optional[Analysis]:
    """Load the demo farm and run a full analysis. Returns None on failure."""
    from .pipeline import run_analysis

    farm = demo_farm()
    costs = finance.default_costs_for(catalog.crop(farm.planned_crop))
    st.session_state["farm"] = farm
    st.session_state["costs"] = costs
    if not run:
        return None
    analysis = run_analysis(farm, costs, use_llm=True)
    set_analysis(analysis)
    db.save(analysis)
    return analysis


def prefill_from_demo() -> None:
    """Prefill the input form with demo values without running an analysis."""
    st.session_state["prefill"] = demo_farm()


def get_scenario() -> Scenario:
    scenario = st.session_state.get("scenario")
    if scenario is None:
        scenario = Scenario()
        st.session_state["scenario"] = scenario
    return scenario
