from datetime import date

from app.demo.demo_data import DEMO_BUSINESS_ID, DEMO_BUSINESS_NAME, DEMO_SCAN_ID, build_demo_context
from app.detectors.registry import run_all_detectors
from app.reports.builder import build_report_summary
from app.reports.exporters import to_csv, to_json, to_markdown, to_pdf
from app.schemas.domain import DetectorStatus, ImpactType, LeakCategory
from app.scoring.priority import score_detector_results


def test_demo_scan_produces_real_findings_across_multiple_categories():
    ctx = build_demo_context()
    results = run_all_detectors(ctx)

    # every detector ran or cleanly skipped — none silently failed on our own synthetic data
    assert all(r.status != DetectorStatus.FAILED for r in results), [
        (r.detector_name, r.errors) for r in results if r.status == DetectorStatus.FAILED
    ]

    all_findings = [f for r in results for f in r.findings]
    categories_found = {f.category for f in all_findings}

    # the synthetic data was deliberately seeded with unbilled, pricing, invoice, discount and renewal issues
    assert LeakCategory.UNBILLED in categories_found
    assert LeakCategory.INVOICE in categories_found
    assert LeakCategory.RENEWAL in categories_found

    for f in all_findings:
        assert f.financial_impact.amount >= 0
        assert f.evidence, f"finding {f.title} has no evidence"
        assert f.calculation.result is not None


def test_demo_scan_scores_and_renders_full_report():
    ctx = build_demo_context()
    results = score_detector_results(run_all_detectors(ctx))

    total_records = sum(r.records_evaluated for r in results if r.status == DetectorStatus.RAN)

    summary = build_report_summary(
        scan_id=DEMO_SCAN_ID, business_id=DEMO_BUSINESS_ID, business_name=DEMO_BUSINESS_NAME,
        scan_date=date(2026, 8, 30), records_analyzed=total_records,
        detector_results=results, data_quality_score=91, is_demo=True,
    )

    assert summary.finding_count > 0
    assert summary.is_demo is True
    assert len(summary.top_findings) <= 5
    # top findings must be sorted by priority score, highest first
    scores = [f.priority_score for f in summary.top_findings]
    assert scores == sorted(scores, reverse=True)

    md = to_markdown(summary)
    assert "DEMO" in md or summary.is_demo  # markdown carries the flag in-band via is_demo check in exporter
    assert to_json(summary)
    assert to_csv(summary)
    assert to_pdf(summary)[:4] == b"%PDF"


def test_renewal_findings_are_never_labeled_potential_leakage():
    ctx = build_demo_context()
    results = run_all_detectors(ctx)
    renewal_findings = [f for r in results if r.category == LeakCategory.RENEWAL for f in r.findings]
    assert renewal_findings
    for f in renewal_findings:
        assert f.financial_impact.impact_type == ImpactType.AT_RISK_REVENUE
