import pytest

from dataclasses import replace

from agripilot.engine import water


def test_efficiency_drives_gross_requirement(farm, rice, weather):
    flood = water.compute(replace(farm, irrigation_method="flood"), rice, weather)
    drip = water.compute(replace(farm, irrigation_method="drip"), rice, weather)
    # Same crop need, but flood loses far more of what is applied.
    assert flood.seasonal_requirement_mm == drip.seasonal_requirement_mm
    assert flood.gross_requirement_mm > drip.gross_requirement_mm
    # Drip applies much smaller doses, so it uses less water across more events.
    assert drip.irrigation_events > flood.irrigation_events
    assert drip.frequency_days < flood.frequency_days


@pytest.mark.parametrize("level", ["abundant", "adequate", "limited", "scarce"])
def test_all_four_availability_levels_produce_a_stress_level(farm, rice, weather, level):
    result = water.compute(replace(farm, water_availability=level), rice, weather)
    assert result.stress_level in {"low", "medium", "high", "critical"}
    assert 0.0 <= result.stress_score <= 1.0


def test_less_water_means_more_stress(farm, rice, weather):
    scores = [
        water.compute(replace(farm, water_availability=level), rice, weather).stress_score
        for level in ("abundant", "adequate", "limited", "scarce")
    ]
    assert scores == sorted(scores)


def test_stage_schedule_covers_the_whole_season(farm, rice, weather):
    result = water.compute(farm, rice, weather)
    assert len(result.stage_schedule) == len(rice.growth_stages)
    assert sum(s["days"] for s in result.stage_schedule) == pytest.approx(
        sum(s["days"] for s in rice.growth_stages)
    )
    assert sum(s["water_mm"] for s in result.stage_schedule) == pytest.approx(
        result.gross_requirement_mm, rel=1e-2
    )


def test_supply_multiplier_reduces_available_water(farm, rice, weather):
    base = water.compute(farm, rice, weather)
    drier = water.compute(farm, rice, weather, supply_multiplier=0.8)
    assert drier.stress_score > base.stress_score


def test_sandy_soil_needs_more_water_than_clay(farm, rice, weather):
    sandy = water.compute(replace(farm, soil_type="sandy"), rice, weather)
    clay = water.compute(replace(farm, soil_type="clay"), rice, weather)
    assert sandy.seasonal_requirement_mm > clay.seasonal_requirement_mm
