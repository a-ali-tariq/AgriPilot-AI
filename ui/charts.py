"""Plotly chart builders. Muted agricultural palette, no animation (PRD §11)."""
from __future__ import annotations

import plotly.graph_objects as go

from agripilot.models import Analysis, FinanceResult, SuitabilityResult, WaterResult

from .theme import ACCENT, BORDER, MUTED, PRIMARY, SEVERITY_COLORS, TEXT, score_color

LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, size=13), margin=dict(l=10, r=10, t=40, b=10),
    hoverlabel=dict(bgcolor="white"),
)


def _grid(fig: go.Figure) -> go.Figure:
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_layout(**LAYOUT)
    return fig


def decision_gauge(score: float, label: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": " / 100", "font": {"size": 34}},
        title={"text": label, "font": {"size": 15, "color": MUTED}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": MUTED},
            "bar": {"color": score_color(score), "thickness": 0.7},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 1, "bordercolor": BORDER,
            "steps": [
                {"range": [0, 45], "color": "#FBECEC"},
                {"range": [45, 70], "color": "#FDF3E2"},
                {"range": [70, 100], "color": "#EDF4EA"},
            ],
        },
    ))
    fig.update_layout(height=240, **LAYOUT)
    return fig


def subscore_bar(suitability: SuitabilityResult) -> go.Figure:
    subs = suitability.subscores()
    names, values = list(subs.keys()), list(subs.values())
    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker_color=[score_color(v) for v in values],
        text=[f"{v:.0f}" for v in values], textposition="outside",
        hovertemplate="%{y}: %{x:.0f}/100<extra></extra>",
    ))
    fig.update_xaxes(range=[0, 112], title="Score out of 100")
    fig.update_layout(height=280, title="What drives this score", showlegend=False)
    return _grid(fig)


def cost_breakdown(finance: FinanceResult, breakdown: dict[str, float], area: float) -> go.Figure:
    items = {k: v * area for k, v in breakdown.items() if v > 0}
    fig = go.Figure(go.Bar(
        x=list(items.keys()), y=list(items.values()),
        marker_color=ACCENT, text=[f"{v:,.0f}" for v in items.values()],
        textposition="outside", hovertemplate="%{x}: PKR %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(height=320, title="Estimated cost breakdown (PKR, whole farm)",
                      showlegend=False)
    fig.update_yaxes(title="PKR")
    return _grid(fig)


def profit_vs_cost(finance: FinanceResult, budget: float) -> go.Figure:
    labels = ["Total cost", "Estimated revenue", "Estimated profit", "Your budget"]
    values = [finance.total_cost, finance.estimated_revenue, finance.estimated_profit, budget]
    colors = [ACCENT, PRIMARY, score_color(70 if finance.estimated_profit > 0 else 20), MUTED]
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors,
        text=[f"{v:,.0f}" for v in values], textposition="outside",
        hovertemplate="%{x}: PKR %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(height=320, title="Money in, money out (estimates)", showlegend=False)
    fig.update_yaxes(title="PKR")
    return _grid(fig)


def stage_water_bars(water: WaterResult) -> go.Figure:
    stages = [s["stage"] for s in water.stage_schedule]
    mm = [s["water_mm"] for s in water.stage_schedule]
    fig = go.Figure(go.Bar(
        x=stages, y=mm, marker_color=PRIMARY,
        text=[f"{v:,.0f} mm" for v in mm], textposition="outside",
        hovertemplate="%{x}<br>%{y:,.0f} mm<extra></extra>",
    ))
    fig.update_layout(height=320, title="Water needed by growth stage", showlegend=False)
    fig.update_yaxes(title="mm of applied water")
    return _grid(fig)


def comparison_bars(rows: list[dict], metric: str, title: str, money: bool = False) -> go.Figure:
    names = [r["crop"] for r in rows]
    values = [r[metric] for r in rows]
    colors = [PRIMARY if v >= 0 else SEVERITY_COLORS["high"] for v in values]
    fig = go.Figure(go.Bar(
        x=names, y=values, marker_color=colors,
        text=[f"{v:,.0f}" for v in values], textposition="outside",
        hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(height=330, title=title, showlegend=False)
    fig.update_yaxes(title="PKR" if money else "")
    return _grid(fig)


def scenario_delta_bars(rows: list[dict]) -> go.Figure:
    shown = [r for r in rows if r["format"] in ("pkr", "qty", "score")]
    labels = [r["metric"] for r in shown]
    changes = [r["pct_change"] for r in shown]
    colors = [
        SEVERITY_COLORS["high"] if r["direction"] == "worse"
        else PRIMARY if r["direction"] == "better" else MUTED
        for r in shown
    ]
    fig = go.Figure(go.Bar(
        x=labels, y=changes, marker_color=colors,
        text=[f"{c:+.1f}%" for c in changes], textposition="outside",
        hovertemplate="%{x}: %{y:+.1f}%<extra></extra>",
    ))
    fig.update_layout(height=340, title="Change vs base scenario", showlegend=False)
    fig.update_yaxes(title="% change")
    return _grid(fig)
