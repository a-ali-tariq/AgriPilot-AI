"""Unit conversions and percentage helpers."""
from __future__ import annotations

ACRE_TO_HECTARE = 0.404686
ACRE_TO_M2 = 4046.86
KANAL_PER_ACRE = 8.0
MAUND_KG = 40.0


def acres_to_hectares(acres: float) -> float:
    return acres * ACRE_TO_HECTARE


def hectares_to_acres(ha: float) -> float:
    return ha / ACRE_TO_HECTARE


def acres_to_m2(acres: float) -> float:
    return acres * ACRE_TO_M2


def kanal_to_acres(kanal: float) -> float:
    return kanal / KANAL_PER_ACRE


def acres_to_kanal(acres: float) -> float:
    return acres * KANAL_PER_ACRE


def mm_over_area_to_liters(mm: float, area_acres: float) -> float:
    """1 mm of depth over 1 m^2 is exactly 1 litre."""
    return mm * acres_to_m2(area_acres)


def maund_to_kg(maunds: float) -> float:
    return maunds * MAUND_KG


def kg_to_maund(kg: float) -> float:
    return kg / MAUND_KG


def pct_change(old: float, new: float) -> float:
    """Percent change from old to new. Returns 0 when old is 0 (undefined)."""
    if old == 0:
        return 0.0
    return (new - old) / abs(old) * 100.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def fmt_pkr(amount: float) -> str:
    """Format PKR with lakh/crore-free plain grouping, for UI and PDF."""
    sign = "-" if amount < 0 else ""
    return f"{sign}PKR {abs(amount):,.0f}"
