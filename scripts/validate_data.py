"""Validate the JSON knowledge base against the schema the engine expects.

Run this after anyone edits agripilot/data/*.json:

    python scripts/validate_data.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agripilot.config import DATA_DIR
from agripilot.models import IRRIGATION_EFFICIENCY, WATER_RANK

VALID_SOILS = {"loamy", "clay", "sandy", "silty", "clay_loam", "sandy_loam"}
VALID_PROVINCES = {"Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan"}
VALID_SEASONS = {"kharif", "rabi", "spring", "annual"}
REQUIRED_COST_KEYS = {"seed", "fertilizer", "labor", "irrigation", "pesticide", "machinery", "other"}

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def load(name: str) -> dict:
    path = DATA_DIR / f"{name}.json"
    if not path.exists():
        err(f"{name}.json is missing")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        err(f"{name}.json is not valid JSON: {exc}")
        return {}


def check_mmdd(value: str, where: str) -> None:
    try:
        month, day = (int(p) for p in value.split("-"))
        date(2001, month, day)
    except Exception:
        err(f"{where}: '{value}' is not a valid MM-DD date")


def check_crops() -> None:
    data = load("crops")
    crops = data.get("crops", [])
    if not crops:
        err("crops.json contains no crops")
        return

    seen: set[str] = set()
    for crop in crops:
        cid = crop.get("id", "<missing id>")
        where = f"crops.json[{cid}]"
        if cid in seen:
            err(f"{where}: duplicate crop id")
        seen.add(cid)

        for field in ("id", "name", "seasons", "sowing_window", "duration_days",
                      "water_need_mm", "water_tolerance", "suitable_soils", "temp_range_c",
                      "typical_yield_per_acre", "typical_price_pkr", "provinces", "growth_stages"):
            if field not in crop:
                err(f"{where}: missing required field '{field}'")

        bad_soils = set(crop.get("suitable_soils", [])) - VALID_SOILS
        if bad_soils:
            err(f"{where}: unknown soil type(s) {sorted(bad_soils)}; valid: {sorted(VALID_SOILS)}")

        bad_provinces = set(crop.get("provinces", [])) - VALID_PROVINCES
        if bad_provinces:
            err(f"{where}: unknown province(s) {sorted(bad_provinces)}")

        bad_seasons = set(crop.get("seasons", [])) - VALID_SEASONS
        if bad_seasons:
            warn(f"{where}: unusual season(s) {sorted(bad_seasons)}")

        if crop.get("water_tolerance") not in WATER_RANK:
            err(f"{where}: water_tolerance must be one of {sorted(WATER_RANK)}")

        window = crop.get("sowing_window", [])
        if len(window) != 2:
            err(f"{where}: sowing_window must be [start, end] in MM-DD form")
        else:
            for value in window:
                check_mmdd(value, where)

        temp = crop.get("temp_range_c", [])
        if len(temp) != 2 or temp[0] >= temp[1]:
            err(f"{where}: temp_range_c must be [min, max] with min < max")

        for field in ("duration_days", "water_need_mm", "typical_yield_per_acre", "typical_price_pkr"):
            value = crop.get(field)
            if isinstance(value, (int, float)) and value <= 0:
                err(f"{where}: {field} must be greater than 0")

        missing_costs = REQUIRED_COST_KEYS - set(crop.get("typical_cost_per_acre_pkr", {}))
        if missing_costs:
            err(f"{where}: typical_cost_per_acre_pkr missing {sorted(missing_costs)}")

        stages = crop.get("growth_stages", [])
        if not stages:
            err(f"{where}: growth_stages must not be empty")
        stage_days = sum(s.get("days", 0) for s in stages)
        duration = crop.get("duration_days", 0)
        if duration and abs(stage_days - duration) > max(10, duration * 0.1):
            warn(f"{where}: growth stage days total {stage_days} but duration_days is {duration}")
        for stage in stages:
            if not 0 < stage.get("kc", 0) <= 1.5:
                warn(f"{where}: stage '{stage.get('name')}' has an unusual Kc of {stage.get('kc')}")

        # A crop nobody can afford at typical prices is usually a data-entry slip.
        cost = sum(crop.get("typical_cost_per_acre_pkr", {}).values())
        revenue = crop.get("typical_yield_per_acre", 0) * crop.get("typical_price_pkr", 0)
        if cost and revenue and revenue < cost * 0.8:
            warn(f"{where}: typical revenue ({revenue:,.0f}) is well below typical cost "
                 f"({cost:,.0f}) — check yield and price")


def check_soils() -> None:
    data = load("soils")
    soils = data.get("soils", {})
    adjacency = data.get("adjacency", {})
    unknown = set(soils) - VALID_SOILS
    if unknown:
        err(f"soils.json: unknown soil type(s) {sorted(unknown)}")
    for soil in VALID_SOILS:
        if soil not in soils:
            err(f"soils.json: missing soil type '{soil}'")
        if soil not in adjacency:
            err(f"soils.json: missing adjacency entry for '{soil}'")
    for soil, neighbours in adjacency.items():
        bad = set(neighbours) - VALID_SOILS
        if bad:
            err(f"soils.json adjacency[{soil}]: unknown soil(s) {sorted(bad)}")


def check_regions() -> None:
    data = load("regions")
    provinces = data.get("provinces", {})
    missing = VALID_PROVINCES - set(provinces)
    if missing:
        err(f"regions.json: missing province(s) {sorted(missing)}")
    for province, districts in provinces.items():
        if not districts:
            err(f"regions.json[{province}]: no districts")
        for district, coords in districts.items():
            where = f"regions.json[{province}][{district}]"
            if not isinstance(coords, list) or len(coords) != 2:
                err(f"{where}: coordinates must be [lat, lon]")
                continue
            lat, lon = coords
            # Pakistan spans roughly 23-37 N, 60-78 E.
            if not 23 <= lat <= 38:
                err(f"{where}: latitude {lat} is outside Pakistan")
            if not 60 <= lon <= 78:
                err(f"{where}: longitude {lon} is outside Pakistan")


def check_mock_weather() -> None:
    data = load("mock_weather")
    provinces = data.get("provinces", {})
    missing = VALID_PROVINCES - set(provinces)
    if missing:
        err(f"mock_weather.json: missing province(s) {sorted(missing)}")
    for province, values in provinces.items():
        where = f"mock_weather.json[{province}]"
        for field in ("avg_temp", "max_temp", "min_temp", "rainfall_mm_30d", "forecast_rain_mm_7d"):
            if field not in values:
                err(f"{where}: missing '{field}'")
        if {"min_temp", "avg_temp", "max_temp"} <= set(values):
            if not values["min_temp"] <= values["avg_temp"] <= values["max_temp"]:
                err(f"{where}: temperatures must satisfy min <= avg <= max")


def check_demo_farm() -> None:
    data = load("demo_farm")
    if not data:
        return
    if data.get("soil_type") not in VALID_SOILS:
        err(f"demo_farm.json: unknown soil_type '{data.get('soil_type')}'")
    if data.get("water_availability") not in WATER_RANK:
        err(f"demo_farm.json: unknown water_availability '{data.get('water_availability')}'")
    if data.get("irrigation_method") not in IRRIGATION_EFFICIENCY:
        err(f"demo_farm.json: unknown irrigation_method '{data.get('irrigation_method')}'")
    if data.get("province") not in VALID_PROVINCES:
        err(f"demo_farm.json: unknown province '{data.get('province')}'")

    crops = {c["id"] for c in load("crops").get("crops", [])}
    if data.get("planned_crop") not in crops:
        err(f"demo_farm.json: planned_crop '{data.get('planned_crop')}' is not in crops.json")

    districts = load("regions").get("provinces", {}).get(data.get("province"), {})
    if data.get("district") not in districts:
        err(f"demo_farm.json: district '{data.get('district')}' is not in regions.json")
    check_mmdd(data.get("sowing_date", ""), "demo_farm.json")


if __name__ == "__main__":
    check_crops()
    check_soils()
    check_regions()
    check_mock_weather()
    check_demo_farm()

    for warning in warnings:
        print(f"WARN   {warning}")
    for error in errors:
        print(f"ERROR  {error}")

    crop_count = len(load("crops").get("crops", []))
    print(f"\n{crop_count} crops checked · {len(errors)} error(s) · {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)
