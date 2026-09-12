import pytest

from agripilot.engine.units import (
    acres_to_hectares, acres_to_m2, clamp, hectares_to_acres, kanal_to_acres,
    kg_to_maund, maund_to_kg, mm_over_area_to_liters, pct_change,
)


def test_area_conversions_roundtrip():
    assert acres_to_hectares(1) == pytest.approx(0.404686)
    assert hectares_to_acres(acres_to_hectares(7.5)) == pytest.approx(7.5)
    assert kanal_to_acres(8) == pytest.approx(1.0)


def test_one_mm_over_one_acre_is_4047_liters():
    # 1 mm depth over 1 m^2 is exactly 1 litre, so 1 acre gives 4046.86 L.
    assert mm_over_area_to_liters(1, 1) == pytest.approx(acres_to_m2(1))
    assert mm_over_area_to_liters(1200, 10) == pytest.approx(1200 * 4046.86 * 10)


def test_maund_conversion():
    assert maund_to_kg(1) == 40
    assert kg_to_maund(400) == 10


def test_pct_change_handles_zero_and_sign():
    assert pct_change(100, 150) == pytest.approx(50.0)
    assert pct_change(100, 50) == pytest.approx(-50.0)
    assert pct_change(0, 500) == 0.0        # undefined -> 0, never a crash
    assert pct_change(-100, -50) == pytest.approx(50.0)


def test_clamp():
    assert clamp(5, 0, 1) == 1
    assert clamp(-5, 0, 1) == 0
    assert clamp(0.5, 0, 1) == 0.5
