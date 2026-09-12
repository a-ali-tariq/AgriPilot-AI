from dataclasses import replace
from datetime import date, timedelta

import pytest

from agripilot.models import CostInputs
from ui import forms


@pytest.fixture
def costs(rice_costs):
    return rice_costs


def test_valid_farm_passes(farm, costs):
    assert forms.validate(farm, costs) == []


def test_zero_and_negative_area_rejected(farm, costs):
    assert forms.validate(replace(farm, area_acres=0), costs)
    assert forms.validate(replace(farm, area_acres=-5), costs)


def test_negative_budget_rejected(farm, costs):
    errors = forms.validate(replace(farm, budget_pkr=-1000), costs)
    assert any("negative" in e.lower() for e in errors)


def test_sowing_date_five_years_ahead_rejected(farm, costs):
    far = replace(farm, sowing_date=date.today() + timedelta(days=5 * 365))
    assert any("within one year" in e for e in forms.validate(far, costs))


def test_district_province_mismatch_rejected(farm, costs):
    # Lahore is in Punjab, not Sindh.
    mismatch = replace(farm, province="Sindh", district="Lahore")
    assert any("not a district" in e for e in forms.validate(mismatch, costs))


def test_negative_cost_rejected(farm, costs):
    bad = replace(costs, fertilizer=-500)
    assert any("Cost cannot be negative" in e for e in forms.validate(farm, bad))


def test_blank_and_overlong_name_rejected(farm, costs):
    assert forms.validate(replace(farm, name="   "), costs)
    assert forms.validate(replace(farm, name="x" * 61), costs)


def test_unknown_crop_rejected(farm, costs):
    assert any("Unknown crop" in e for e in forms.validate(replace(farm, planned_crop="mango"), costs))
