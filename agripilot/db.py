"""SQLite persistence for recent analyses (PRD §6 "Recent analyses").

Stores no personal data beyond the farm name (PRD §9). Every function fails
soft: if SQLite is unavailable the app simply hides the recent-analyses panel.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import asdict
from datetime import date, datetime
from typing import Any, Optional

from .config import DB_PATH
from .models import (
    Analysis, ClimateRisk, CostInputs, CropSpec, Farm, FinanceResult,
    SuitabilityResult, WaterResult, WeatherSummary,
)

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at     TEXT NOT NULL,
  farm_name      TEXT NOT NULL,
  district       TEXT,
  crop_id        TEXT,
  crop_name      TEXT,
  decision_score REAL,
  decision_label TEXT,
  is_demo        INTEGER DEFAULT 0,
  payload_json   TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def _default(obj: Any):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Not JSON serialisable: {type(obj)}")


def to_json(analysis: Analysis) -> str:
    return json.dumps(asdict(analysis), default=_default)


def from_json(raw: str) -> Analysis:
    d = json.loads(raw)
    farm = Farm(**{**d["farm"], "sowing_date": date.fromisoformat(d["farm"]["sowing_date"])})
    return Analysis(
        farm=farm,
        costs=CostInputs(**d["costs"]),
        crop=CropSpec(**{**d["crop"],
                         "sowing_window": tuple(d["crop"]["sowing_window"]),
                         "temp_range_c": tuple(d["crop"]["temp_range_c"])}),
        weather=WeatherSummary(**d["weather"]),
        suitability=SuitabilityResult(**d["suitability"]),
        finance=FinanceResult(**d["finance"]),
        water=WaterResult(**d["water"]),
        climate_risks=[ClimateRisk(**r) for r in d["climate_risks"]],
        climate_risk_score=d["climate_risk_score"],
        decision_score=d["decision_score"],
        decision_label=d["decision_label"],
        alternatives=[SuitabilityResult(**a) for a in d.get("alternatives", [])],
        ai_explanation=d.get("ai_explanation"),
        ai_next_steps=d.get("ai_next_steps"),
        ai_source=d.get("ai_source", "deterministic"),
        created_at=d.get("created_at", ""),
    )


def save(analysis: Analysis) -> Optional[int]:
    try:
        with _connect() as conn:
            cur = conn.execute(
                "INSERT INTO analyses (created_at, farm_name, district, crop_id, crop_name,"
                " decision_score, decision_label, is_demo, payload_json)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    analysis.created_at or datetime.now().isoformat(timespec="seconds"),
                    analysis.farm.name, analysis.farm.district,
                    analysis.crop.id, analysis.crop.name,
                    analysis.decision_score, analysis.decision_label,
                    int(analysis.farm.is_demo), to_json(analysis),
                ),
            )
            return cur.lastrowid
    except Exception as exc:
        log.warning("Could not save analysis: %s", exc)
        return None


def recent(n: int = 5) -> list[dict[str, Any]]:
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT id, created_at, farm_name, district, crop_name, decision_score,"
                " decision_label, is_demo FROM analyses ORDER BY id DESC LIMIT ?", (n,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        log.warning("Could not read recent analyses: %s", exc)
        return []


def get(analysis_id: int) -> Optional[Analysis]:
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM analyses WHERE id = ?", (analysis_id,)
            ).fetchone()
            return from_json(row["payload_json"]) if row else None
    except Exception as exc:
        log.warning("Could not load analysis %s: %s", analysis_id, exc)
        return None
