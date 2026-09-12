"""Loads and caches the JSON knowledge base (crops, soils, regions, weather).

Pure file I/O with no external calls, so the engine may import this.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import DATA_DIR
from .models import CropSpec


@lru_cache(maxsize=None)
def _load(name: str) -> dict[str, Any]:
    with open(DATA_DIR / f"{name}.json", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def crops() -> dict[str, CropSpec]:
    return {c["id"]: CropSpec.from_dict(c) for c in _load("crops")["crops"]}


def crop(crop_id: str) -> CropSpec:
    try:
        return crops()[crop_id]
    except KeyError:
        raise KeyError(f"Unknown crop id '{crop_id}'. Known: {sorted(crops())}") from None


def crops_for_province(province: str) -> list[CropSpec]:
    return [c for c in crops().values() if province in c.provinces]


def soils() -> dict[str, dict[str, Any]]:
    return _load("soils")["soils"]


def soil_adjacency() -> dict[str, list[str]]:
    return _load("soils")["adjacency"]


def soil_water_factor(soil_type: str) -> float:
    return float(soils().get(soil_type, {}).get("water_factor", 1.0))


def soil_label(soil_type: str) -> str:
    return soils().get(soil_type, {}).get("label", soil_type.replace("_", " ").title())


def provinces() -> list[str]:
    return list(_load("regions")["provinces"].keys())


def districts(province: str) -> list[str]:
    return list(_load("regions")["provinces"].get(province, {}).keys())


def district_coords(province: str, district: str) -> tuple[float, float] | None:
    coords = _load("regions")["provinces"].get(province, {}).get(district)
    return (coords[0], coords[1]) if coords else None


def mock_weather(province: str) -> dict[str, Any]:
    table = _load("mock_weather")["provinces"]
    return dict(table.get(province, table["Punjab"]))


def demo_farm_raw() -> dict[str, Any]:
    return dict(_load("demo_farm"))
