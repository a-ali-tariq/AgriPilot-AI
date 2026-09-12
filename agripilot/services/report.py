"""PDF report generation with reportlab (FR-10, PRD §5.10).

Pure reportlab — no kaleido, no headless browser — so it works on Streamlit
Community Cloud without system packages.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from ..config import CROP_HEALTH_DISCLAIMER, DISCLAIMER
from ..engine import climate as climate_engine
from ..models import Analysis

PRIMARY = colors.HexColor("#2E7D32")
ACCENT = colors.HexColor("#8D6E63")
BORDER = colors.HexColor("#D9E0D4")
MUTED = colors.HexColor("#5F6B5F")
SEVERITY = {
    "low": colors.HexColor("#2E7D32"), "medium": colors.HexColor("#E58A00"),
    "high": colors.HexColor("#C62828"), "critical": colors.HexColor("#8E0000"),
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("apTitle", parent=base["Title"], fontSize=22,
                                textColor=PRIMARY, spaceAfter=2),
        "subtitle": ParagraphStyle("apSubtitle", parent=base["Normal"], fontSize=10,
                                   textColor=MUTED, spaceAfter=14),
        "h2": ParagraphStyle("apH2", parent=base["Heading2"], fontSize=13,
                             textColor=PRIMARY, spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("apH3", parent=base["Heading3"], fontSize=11,
                             textColor=colors.HexColor("#1F2A1F"), spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("apBody", parent=base["Normal"], fontSize=9.5, leading=14,
                               alignment=TA_LEFT),
        "small": ParagraphStyle("apSmall", parent=base["Normal"], fontSize=8,
                                textColor=MUTED, leading=11),
        "demo": ParagraphStyle("apDemo", parent=base["Normal"], fontSize=9,
                               textColor=colors.HexColor("#7A5200"), spaceAfter=8),
    }


def _table(rows: list[list[Any]], widths: list[float], header: bool = True) -> Table:
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2A1F")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    table.setStyle(TableStyle(style))
    return table


def _pkr(value: float) -> str:
    return f"PKR {value:,.0f}"


def _bar(label: str, value: float, maximum: float = 100.0, width: float = 60 * mm) -> Table:
    """A score bar drawn as a two-cell table — no image dependency."""
    filled = max(0.0, min(1.0, value / maximum))
    bar = Table([[""]], colWidths=[width * filled or 0.1], rowHeights=[4 * mm])
    color = SEVERITY["low"] if value >= 70 else SEVERITY["medium"] if value >= 45 else SEVERITY["high"]
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color),
                             ("LINEBELOW", (0, 0), (-1, -1), 0, colors.white)]))
    wrapper = Table([[label, bar, f"{value:.0f}"]],
                    colWidths=[32 * mm, width, 12 * mm], hAlign="LEFT")
    wrapper.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    return wrapper


def build_pdf(
    analysis: Analysis,
    comparison: Optional[list[dict]] = None,
    scenario_diff: Optional[list[dict]] = None,
    crop_health: Optional[dict] = None,
) -> bytes:
    """Render the full farm report. Sections follow PRD §5.10 order."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
        title=f"AgriPilot AI report — {analysis.farm.name}", author="AgriPilot AI",
    )
    s = _styles()
    story: list[Any] = []
    farm, crop, fin, wat = analysis.farm, analysis.crop, analysis.finance, analysis.water
    content_width = doc.width

    # --- header ---------------------------------------------------------------
    story.append(Paragraph("AgriPilot AI — Farm Analysis Report", s["title"]))
    story.append(Paragraph(
        f"{farm.name} · {farm.district}, {farm.province} · generated "
        f"{datetime.now():%d %B %Y}", s["subtitle"]))
    if farm.is_demo:
        story.append(Paragraph(
            "<b>DEMO FARM</b> — this report uses sample data from the project brief, "
            "not a real farm.", s["demo"]))

    # --- 1. farm information --------------------------------------------------
    story.append(Paragraph("1. Farm information", s["h2"]))
    story.append(_table([
        ["Field", "Value", "Field", "Value"],
        ["Farm name", farm.name, "Soil type", farm.soil_type.replace("_", " ").title()],
        ["Location", f"{farm.district}, {farm.province}",
         "Water availability", farm.water_availability.title()],
        ["Area", f"{farm.area_acres:g} acres", "Irrigation", farm.irrigation_method.title()],
        ["Planned crop", crop.name, "Sowing date", f"{farm.sowing_date:%d %b %Y}"],
        ["Budget", _pkr(farm.budget_pkr), "Season", ", ".join(crop.seasons).title()],
    ], [content_width * w for w in (0.18, 0.32, 0.18, 0.32)]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Weather data source: "
        + ("live (OpenWeatherMap)" if analysis.weather.source == "live"
           else "demo data — live weather source was unavailable")
        + f". Average {analysis.weather.avg_temp:.0f}°C, range "
          f"{analysis.weather.min_temp:.0f}–{analysis.weather.max_temp:.0f}°C, "
          f"rainfall {analysis.weather.rainfall_mm_30d:.0f} mm over 30 days.",
        s["small"]))

    # --- 2. crop recommendation ----------------------------------------------
    story.append(Paragraph("2. Crop recommendation", s["h2"]))
    story.append(Paragraph(
        f"<b>{crop.name}</b> scores <b>{analysis.suitability.score:.0f}/100</b> for suitability "
        f"on this farm. Overall Farm Decision Score: <b>{analysis.decision_score:.0f}/100 — "
        f"{analysis.decision_label}</b>.", s["body"]))
    story.append(Spacer(1, 4))
    for label, value in analysis.suitability.subscores().items():
        story.append(_bar(label, value))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Reasons behind these scores", s["h3"]))
    for reason in analysis.suitability.reasons:
        story.append(Paragraph(f"• {reason}", s["body"]))
    if analysis.suitability.warnings:
        story.append(Paragraph("Warnings", s["h3"]))
        for warning in analysis.suitability.warnings:
            story.append(Paragraph(f"• {warning}", s["body"]))

    if analysis.alternatives:
        story.append(Paragraph("Alternative crops considered", s["h3"]))
        story.append(_table(
            [["Crop", "Suitability"]] +
            [[alt.crop_name, f"{alt.score:.0f}/100"] for alt in analysis.alternatives[:5]],
            [content_width * 0.6, content_width * 0.4]))

    # --- 3. crop comparison ---------------------------------------------------
    if comparison:
        story.append(Paragraph("3. Crop comparison", s["h2"]))
        story.append(_table(
            [["Crop", "Suitability", "Water (mm)", "Est. cost", "Est. profit", "Risk"]] +
            [[r["crop"], f"{r['suitability']:.0f}", f"{r['water_mm']:,.0f}",
              _pkr(r["cost"]), _pkr(r["profit"]), r["risk"].title()] for r in comparison],
            [content_width * w for w in (0.26, 0.14, 0.14, 0.17, 0.17, 0.12)]))
        story.append(Paragraph(
            "Each crop is costed with its own typical inputs and typical market price.",
            s["small"]))

    # --- 4. irrigation --------------------------------------------------------
    story.append(Paragraph("4. Irrigation analysis", s["h2"]))
    story.append(_table([
        ["Measure", "Value"],
        ["Crop water requirement", f"{wat.seasonal_requirement_mm:,.0f} mm for the season"],
        ["Effective rainfall", f"{wat.effective_rainfall_mm:,.0f} mm"],
        ["Water to apply", f"{wat.gross_requirement_mm:,.0f} mm "
                           f"({wat.seasonal_requirement_liters / 1e6:,.1f} million litres)"],
        ["Irrigation events", f"{wat.irrigation_events}, about one every {wat.frequency_days} days"],
        ["Water stress", f"{wat.stress_level.title()} (index {wat.stress_score:.2f} of 1.00)"],
    ], [content_width * 0.32, content_width * 0.68]))
    if wat.stage_schedule:
        story.append(Spacer(1, 4))
        story.append(_table(
            [["Growth stage", "Days", "Water (mm)", "Irrigations"]] +
            [[st["stage"], str(st["days"]), f"{st['water_mm']:,.0f}", str(st["events"])]
             for st in wat.stage_schedule],
            [content_width * w for w in (0.46, 0.14, 0.2, 0.2)]))
    if wat.savings_tips:
        story.append(Paragraph("Water-saving suggestions", s["h3"]))
        for tip in wat.savings_tips:
            story.append(Paragraph(f"• {tip}", s["body"]))

    story.append(PageBreak())

    # --- 5. climate risk ------------------------------------------------------
    story.append(Paragraph("5. Climate risk", s["h2"]))
    if analysis.climate_risks:
        story.append(Paragraph(
            f"Overall climate risk: <b>{climate_engine.overall_severity(analysis.climate_risks).title()}</b> "
            f"({len(analysis.climate_risks)} risk(s) identified).", s["body"]))
        for risk in analysis.climate_risks:
            story.append(KeepTogether([
                Paragraph(f"{risk.name} — {risk.severity.upper()} "
                          f"(rule confidence {risk.probability:.0%})", s["h3"]),
                Paragraph(f"<b>Possible impact:</b> {risk.impact}", s["body"]),
                Paragraph(f"<b>Suggested action:</b> {risk.action}", s["body"]),
            ]))
    else:
        story.append(Paragraph(
            "No significant climate risks were identified for this crop, location and season.",
            s["body"]))

    # --- 6. financial analysis ------------------------------------------------
    story.append(Paragraph("6. Financial analysis", s["h2"]))
    story.append(_table([
        ["Measure", "Estimate", "Measure", "Estimate"],
        ["Total cost", _pkr(fin.total_cost), "Cost per acre", _pkr(fin.cost_per_acre)],
        ["Estimated yield", f"{fin.estimated_yield:,.0f} {fin.yield_unit}",
         "Price assumed", f"{_pkr(fin.price_per_unit)} per {fin.yield_unit}"],
        ["Estimated revenue", _pkr(fin.estimated_revenue),
         "Estimated profit", _pkr(fin.estimated_profit)],
        ["Profit per acre", _pkr(fin.profit_per_acre), "Return on investment", f"{fin.roi_pct:.0f}%"],
        ["Your budget", _pkr(farm.budget_pkr),
         "Budget gap", _pkr(fin.budget_gap) + (" (over budget)" if fin.budget_gap < 0 else "")],
    ], [content_width * w for w in (0.2, 0.3, 0.2, 0.3)]))
    story.append(Spacer(1, 3))
    story.append(Paragraph("Cost breakdown, per acre", s["h3"]))
    story.append(_table(
        [["Item", "Per acre", f"Whole farm ({farm.area_acres:g} acres)"]] +
        [[name, _pkr(value), _pkr(value * farm.area_acres)]
         for name, value in analysis.costs.breakdown().items() if value > 0],
        [content_width * 0.34, content_width * 0.33, content_width * 0.33]))
    story.append(Paragraph("All financial figures are estimates, not guarantees.", s["small"]))

    # --- 7. what-if -----------------------------------------------------------
    if scenario_diff:
        story.append(Paragraph("7. What-If simulation", s["h2"]))
        story.append(_table(
            [["Metric", "Base", "Scenario", "Change"]] +
            [[r["metric"], f"{r['base']:,.1f}", f"{r['scenario']:,.1f}",
              f"{r['pct_change']:+.1f}%"] for r in scenario_diff],
            [content_width * w for w in (0.34, 0.22, 0.22, 0.22)]))

    # --- 8. crop health -------------------------------------------------------
    if crop_health and crop_health.get("available"):
        story.append(Paragraph("8. Crop health image assessment", s["h2"]))
        story.append(Paragraph(
            f"<b>{crop_health['condition']}</b> — confidence {crop_health['confidence']:.0%}, "
            f"possible severity {crop_health.get('severity', 'unknown')}.", s["body"]))
        for symptom in crop_health.get("symptoms", []):
            story.append(Paragraph(f"• {symptom}", s["body"]))
        story.append(Paragraph(f"<i>{CROP_HEALTH_DISCLAIMER}</i>", s["small"]))

    # --- 9. feasibility score + final recommendation --------------------------
    story.append(Paragraph("9. Feasibility score and final recommendation", s["h2"]))
    story.append(_bar("Decision score", analysis.decision_score))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>{analysis.decision_label}</b> — Farm Decision Score "
        f"{analysis.decision_score:.0f}/100.", s["body"]))
    if analysis.ai_explanation:
        for para in analysis.ai_explanation.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), s["body"]))
        story.append(Paragraph(
            "Explanation written by the AI model from the calculated results."
            if analysis.ai_source == "llm" else
            "Explanation generated by the calculation engine.", s["small"]))

    # --- 10. action plan ------------------------------------------------------
    story.append(Paragraph("10. Action plan", s["h2"]))
    for index, step in enumerate(analysis.ai_next_steps or [], start=1):
        story.append(Paragraph(f"{index}. {step}", s["body"]))

    # --- 11. disclaimer -------------------------------------------------------
    story.append(Spacer(1, 10))
    story.append(Paragraph("Disclaimer", s["h2"]))
    story.append(Paragraph(DISCLAIMER, s["small"]))

    def _footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, "AgriPilot AI — decision-support estimates")
        if farm.is_demo:
            canvas.drawCentredString(A4[0] / 2, 10 * mm, "DEMO FARM — sample data")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
