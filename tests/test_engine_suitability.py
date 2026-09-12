import pytest

from agripilot import catalog
from agripilot.engine import suitability


def test_score_is_deterministic_and_in_range(farm, rice, weather):
    first = suitability.score_crop(farm, rice, weather)
    second = suitability.score_crop(farm, rice, weather)
    assert first == second
    assert 0 <= first.score <= 100
    assert all(0 <= v <= 100 for v in first.subscores().values())


def test_every_subscore_produces_a_reason(farm, rice, weather):
    result = suitability.score_crop(farm, rice, weather)
    assert len(result.reasons) == len(result.subscores())
    assert all(r.strip() for r in result.reasons)


def test_suitable_soil_beats_unsuitable_soil(farm, weather):
    from dataclasses import replace

    rice = catalog.crop("rice")            # prefers clay / clay_loam / loamy
    good = suitability.score_crop(replace(farm, soil_type="loamy"), rice, weather)
    bad = suitability.score_crop(replace(farm, soil_type="sandy"), rice, weather)
    assert good.soil_score > bad.soil_score
    assert good.score > bad.score


def test_more_water_never_scores_worse(farm, rice, weather):
    from dataclasses import replace

    scores = [
        suitability.score_crop(replace(farm, water_availability=level), rice, weather).water_score
        for level in ("scarce", "limited", "adequate", "abundant")
    ]
    assert scores == sorted(scores)


def test_sowing_outside_window_is_penalised(farm, rice, weather):
    from dataclasses import replace
    from datetime import date

    year = date.today().year
    inside = suitability.score_crop(replace(farm, sowing_date=date(year, 7, 15)), rice, weather)
    outside = suitability.score_crop(replace(farm, sowing_date=date(year, 11, 15)), rice, weather)
    assert inside.season_score == 100.0
    assert outside.season_score < inside.season_score


def test_ranking_is_sorted_and_excludes_current_crop(farm, weather):
    ranked = suitability.rank_crops(farm, weather, top_n=5, exclude="rice")
    assert len(ranked) <= 5
    assert all(r.crop_id != "rice" for r in ranked)
    assert [r.score for r in ranked] == sorted((r.score for r in ranked), reverse=True)


@pytest.mark.parametrize("province", ["Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan"])
def test_every_province_has_scoreable_crops(farm, weather, province):
    from dataclasses import replace

    local = replace(farm, province=province, district=catalog.districts(province)[0])
    ranked = suitability.rank_crops(local, weather, top_n=3)
    assert ranked, f"no crops rankable in {province}"
