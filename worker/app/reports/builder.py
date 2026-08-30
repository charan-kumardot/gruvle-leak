"""
Assembles a ReportSummary from scan results. Pure function, no I/O — takes
already-computed findings (scored, evidence-backed) and detector run results,
and produces the shape every export format (PDF/CSV/JSON/Markdown) renders
from. This guarantees every export is consistent with every other, because
they all render the same object instead of re-deriving numbers independently.
"""
from __future__ import annotations

from datetime import date

from app.reports.schemas import ImpactTotal, ReportSummary, confidence_rank
from app.schemas.domain import Confidence, DetectorRunResult, DetectorStatus, LeakFinding
from app.scoring.priority import total_impact_by_type

TOP_FINDINGS_COUNT = 5


def build_report_summary(
    *,
    scan_id: str,
    business_id: str,
    business_name: str,
    scan_date: date,
    records_analyzed: int,
    detector_results: list[DetectorRunResult],
    data_quality_score: int | None,
    is_demo: bool = False,
) -> ReportSummary:
    findings: list[LeakFinding] = [f for r in detector_results for f in r.findings]

    detectors_run = [r.detector_name for r in detector_results if r.status == DetectorStatus.RAN]
    detectors_skipped = [
        f"{r.detector_name} ({r.skip_reason})"
        for r in detector_results
        if r.status in (DetectorStatus.SKIPPED_MISSING_FIELDS, DetectorStatus.SKIPPED_NOT_IMPLEMENTED)
    ]
    detector_failures = [f"{r.detector_name}: {'; '.join(r.errors)}" for r in detector_results if r.status == DetectorStatus.FAILED]

    totals = total_impact_by_type(findings)
    impact_totals = [
        ImpactTotal(impact_type=impact_type, currency=currency, amount=amount)
        for impact_type, by_currency in totals.items()
        for currency, amount in by_currency.items()
    ]

    ranked = sorted(findings, key=lambda f: (-f.priority_score, confidence_rank(f.confidence)))
    top_findings = ranked[:TOP_FINDINGS_COUNT]

    high_confidence_count = sum(1 for f in findings if f.confidence == Confidence.HIGH)

    data_limitations = list(detectors_skipped)
    if detector_failures:
        data_limitations.append(
            "Some checks could not complete due to an internal error and were excluded from this report: "
            + "; ".join(detector_failures)
        )
    if not findings:
        data_limitations.append("No significant revenue leakage was found in the data and detectors available for this scan.")

    return ReportSummary(
        scan_id=scan_id,
        business_id=business_id,
        business_name=business_name,
        scan_date=scan_date,
        records_analyzed=records_analyzed,
        detectors_run=detectors_run,
        detectors_skipped=detectors_skipped,
        data_quality_score=data_quality_score,
        impact_totals=impact_totals,
        finding_count=len(findings),
        high_confidence_count=high_confidence_count,
        top_findings=top_findings,
        all_findings=ranked,
        data_limitations=data_limitations,
        is_demo=is_demo,
    )
