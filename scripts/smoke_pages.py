"""Headless render check: runs each Streamlit page and reports any exception."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from streamlit.testing.v1 import AppTest

from agripilot import catalog
from agripilot.engine import finance
from agripilot.models import Farm
from agripilot.pipeline import run_analysis
from agripilot.state import demo_farm

TIMEOUT = 60


def build_analysis():
    farm = demo_farm()
    costs = finance.default_costs_for(catalog.crop(farm.planned_crop))
    return run_analysis(farm, costs, use_llm=True)


def check(path: str, analysis=None) -> bool:
    app = AppTest.from_file(path, default_timeout=TIMEOUT)
    if analysis is not None:
        app.session_state["analysis"] = analysis
        app.session_state["farm"] = analysis.farm
        app.session_state["costs"] = analysis.costs
    app.run()
    if app.exception:
        print(f"FAIL  {path}")
        for exc in app.exception:
            print(f"      {exc.value}")
        return False
    warnings = [w.value for w in app.warning] if hasattr(app, "warning") else []
    print(f"ok    {path}   ({len(app.markdown)} markdown, {len(app.button)} buttons)")
    return True


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    empty_session = "--empty" in sys.argv

    pages = args or ["Home.py"] + sorted(str(p) for p in Path("pages").glob("*.py"))
    analysis = None if empty_session else build_analysis()
    if empty_session:
        print("Running with an EMPTY session: every page must show an empty state, "
              "not a traceback.\n")

    results = [check(p, analysis) for p in pages]
    print("\n" + ("ALL PAGES RENDER" if all(results) else "SOME PAGES FAILED"))
    sys.exit(0 if all(results) else 1)
