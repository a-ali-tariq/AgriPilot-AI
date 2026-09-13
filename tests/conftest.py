import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agripilot import catalog
from agripilot.engine import finance
from agripilot.models import Farm, WeatherSummary


@pytest.fixture(autouse=True)
def no_external_keys(monkeypatch):
    """Run every test as if no API keys are configured.

    Without this, the suite's results depend on whether the developer happens to
    have a key in .streamlit/secrets.toml, and it would make real network calls,
    which is both slow and flaky. The fallback paths are what we assert on, so
    they must be the paths the tests actually take.
    """
    import agripilot.config as config

    monkeypatch.setattr(config, "_secrets_file", lambda: {})
    for key in ("OPENWEATHER_API_KEY", "LLM_API_KEY", "LLM_PROVIDER",
                "LLM_MODEL", "VISION_MODEL"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def farm() -> Farm:
    """The PRD §13 demo farm. Sowing is 15 July of the current year, which keeps the
    farm inside rice's sowing window and inside the +/- 1 year validation limit."""
    return Farm(
        name="Demo Farm", province="Sindh", district="Hyderabad", area_acres=10.0,
        soil_type="loamy", water_availability="limited", irrigation_method="flood",
        planned_crop="rice", sowing_date=date(date.today().year, 7, 15), budget_pkr=500_000.0,
        lat=25.396, lon=68.3578, is_demo=True,
    )


@pytest.fixture
def weather() -> WeatherSummary:
    return WeatherSummary(**catalog.mock_weather("Sindh"))


@pytest.fixture
def rice():
    return catalog.crop("rice")


@pytest.fixture
def rice_costs(rice):
    return finance.default_costs_for(rice)
