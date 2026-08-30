"""
Export ReportSummary to the four formats spec section 44 requires. Every
exporter renders the exact same ReportSummary object — no format re-derives
numbers, so PDF/CSV/JSON/Markdown can never disagree with each other.
"""
from __future__ import annotations

import csv
import io
import json

from app.reports.schemas import ReportSummary

DISCLAIMER = (
    "Gruvle identifies potential revenue leakage from the data you provide. Findings may require human "
    "review and should not be treated as accounting, tax, legal, or financial advice."
)


def to_json(summary: ReportSummary) -> str:
    return summary.model_dump_json(indent=2)


def to_markdown(summary: ReportSummary) -> str:
    lines = [
        f"# Revenue Leakage Report — {summary.business_name}",
        "",
        f"Scan date: {summary.scan_date.isoformat()}" + ("  \n**DEMO DATA**" if summary.is_demo else ""),
        f"Records analyzed: {summary.records_analyzed:,}",
        "",
        "## Executive Summary",
        "",
        f"{summary.finding_count} finding(s) identified, {summary.high_confidence_count} at high confidence.",
        "",
    ]
    if summary.impact_totals:
        lines.append("| Impact Type | Amount |")
        lines.append("|---|---|")
        for t in summary.impact_totals:
            lines.append(f"| {t.impact_type.replace('_', ' ').title()} | {t.currency} {t.amount:,} |")
        lines.append("")

    if summary.data_quality_score is not None:
        lines.append(f"**Data quality score:** {summary.data_quality_score}/100")
        lines.append("")

    lines.append("## Fix These First")
    lines.append("")
    for i, f in enumerate(summary.top_findings, start=1):
        lines.append(
            f"{i}. **{f.title}** — {f.financial_impact.currency} {f.financial_impact.amount:,} "
            f"({f.confidence.value.title()} confidence, priority {f.priority_score})"
        )
        lines.append(f"   {f.summary}")
    lines.append("")

    lines.append("## All Findings")
    lines.append("")
    for f in summary.all_findings:
        lines.append(f"### {f.title} ({f.category.value})")
        lines.append("")
        lines.append(f"- **Impact:** {f.financial_impact.impact_type.value.replace('_', ' ').title()} — "
                      f"{f.financial_impact.currency} {f.financial_impact.amount:,}"
                      + (f"/{f.financial_impact.recurrence_period}" if f.financial_impact.is_recurring else ""))
        lines.append(f"- **Confidence:** {f.confidence.value} — {f.confidence_explanation}")
        lines.append(f"- **Why it matters:** {f.why_it_matters}")
        lines.append(f"- **Calculation:** {f.calculation.formula}")
        lines.append(f"- **Evidence records:** {len(f.evidence)}")
        if f.what_we_dont_know:
            lines.append(f"- **What we don't know:** {'; '.join(f.what_we_dont_know)}")
        lines.append(f"- **Recommended action:** {f.recommended_action}")
        lines.append("")

    lines.append("## Data Limitations")
    lines.append("")
    for limitation in summary.data_limitations:
        lines.append(f"- {limitation}")
    lines.append("")

    lines.append("---")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def to_csv(summary: ReportSummary) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "title", "category", "impact_type", "amount", "currency", "is_recurring", "recurrence_period",
        "confidence", "priority_score", "status", "evidence_count", "recommended_action",
    ])
    for f in summary.all_findings:
        writer.writerow([
            f.title, f.category.value, f.financial_impact.impact_type.value, f.financial_impact.amount,
            f.financial_impact.currency, f.financial_impact.is_recurring, f.financial_impact.recurrence_period or "",
            f.confidence.value, f.priority_score, f.status.value, len(f.evidence), f.recommended_action,
        ])
    return buf.getvalue()


def to_pdf(summary: ReportSummary) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = []

    title = f"Revenue Leakage Report — {summary.business_name}"
    if summary.is_demo:
        title += "  [DEMO DATA]"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph(f"Scan date: {summary.scan_date.isoformat()} · Records analyzed: {summary.records_analyzed:,}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(
        f"{summary.finding_count} finding(s) identified, {summary.high_confidence_count} at high confidence.",
        styles["Normal"],
    ))
    story.append(Spacer(1, 8))

    if summary.impact_totals:
        data = [["Impact Type", "Amount"]] + [
            [t.impact_type.replace("_", " ").title(), f"{t.currency} {t.amount:,}"] for t in summary.impact_totals
        ]
        table = Table(data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    story.append(Paragraph("Fix These First", styles["Heading2"]))
    for i, f in enumerate(summary.top_findings, start=1):
        story.append(Paragraph(
            f"{i}. <b>{f.title}</b> — {f.financial_impact.currency} {f.financial_impact.amount:,} "
            f"({f.confidence.value.title()} confidence)",
            styles["Normal"],
        ))
        story.append(Paragraph(f.summary, styles["Normal"]))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Data Limitations", styles["Heading2"]))
    for limitation in summary.data_limitations:
        story.append(Paragraph(f"• {limitation}", styles["Normal"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph(DISCLAIMER, styles["Italic"]))

    doc.build(story)
    return buf.getvalue()
