from datetime import date
from decimal import Decimal

from app.reports.builder import build_report_summary
from app.reports.exporters import to_csv, to_json, to_markdown, to_pdf
from app.schemas.domain import (
    Calculation,
    Confidence,
    DetectorRunResult,
    DetectorStatus,
    FinancialImpact,
    ImpactType,
    LeakCategory,
    LeakFinding,
)
from app.scoring.priority import score_findings


def _sample_detector_results():
    finding = LeakFinding(
        id="f1", scan_id="scan1", business_id="biz1", category=LeakCategory.UNBILLED,
        title="Potential unbilled revenue", summary="27 orders totalling INR 84,000 have no matching invoice.",
        why_it_matters="Money may go uncollected.", recommended_action="Issue invoices.",
        financial_impact=FinancialImpact(impact_type=ImpactType.POTENTIAL_LEAKAGE, amount=Decimal("84000"), currency="INR"),
        confidence=Confidence.HIGH, confidence_explanation="Direct join on order_id.",
        urgency=0.8, recoverability=0.9, priority_score=0.0,
        evidence=[], calculation=Calculation(method="sum", formula="27 orders = 84000", result=Decimal("84000")),
        detection_method="join", source_dataset_ids=["orders.csv"],
    )
    scored = score_findings([finding])
    return [
        DetectorRunResult(detector_name="UnbilledRevenueDetector", category=LeakCategory.UNBILLED,
                           status=DetectorStatus.RAN, findings=scored, records_evaluated=100),
        DetectorRunResult(detector_name="InventoryLeakDetector", category=LeakCategory.INVENTORY,
                           status=DetectorStatus.SKIPPED_NOT_IMPLEMENTED, skip_reason="Not yet implemented."),
    ]


def test_build_and_export_all_formats():
    summary = build_report_summary(
        scan_id="scan1", business_id="biz1", business_name="Demo Retail Co.",
        scan_date=date(2026, 1, 1), records_analyzed=48291,
        detector_results=_sample_detector_results(), data_quality_score=87,
    )

    assert summary.finding_count == 1
    assert summary.high_confidence_count == 1
    assert len(summary.impact_totals) == 1
    assert summary.impact_totals[0].amount == Decimal("84000")
    assert "InventoryLeakDetector (Not yet implemented.)" in summary.data_limitations

    md = to_markdown(summary)
    assert "Potential unbilled revenue" in md
    assert "84,000" in md
    assert "should not be treated as accounting, tax, legal, or financial advice" in md

    js = to_json(summary)
    assert "84000" in js

    csv_text = to_csv(summary)
    assert "Potential unbilled revenue" in csv_text

    pdf_bytes = to_pdf(summary)
    assert pdf_bytes[:4] == b"%PDF"


def test_no_findings_never_fabricated():
    summary = build_report_summary(
        scan_id="scan2", business_id="biz1", business_name="Demo Retail Co.",
        scan_date=date(2026, 1, 1), records_analyzed=100, detector_results=[], data_quality_score=90,
    )
    assert summary.finding_count == 0
    assert any("no significant revenue leakage" in d.lower() for d in summary.data_limitations)
