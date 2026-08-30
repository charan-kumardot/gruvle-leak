from decimal import Decimal

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
from app.scoring.priority import score_detector_results, score_findings, total_impact_by_type


def _finding(amount: str, confidence: Confidence, urgency: float, recoverability: float,
             impact_type: ImpactType = ImpactType.POTENTIAL_LEAKAGE, currency: str = "INR") -> LeakFinding:
    return LeakFinding(
        id=f"f-{amount}-{confidence}", scan_id="s1", business_id="b1", category=LeakCategory.UNBILLED,
        title="t", summary="s", why_it_matters="w", recommended_action="a",
        financial_impact=FinancialImpact(impact_type=impact_type, amount=Decimal(amount), currency=currency),
        confidence=confidence, confidence_explanation="x",
        urgency=urgency, recoverability=recoverability, priority_score=0.0,
        evidence=[], calculation=Calculation(method="m", formula="f", result=Decimal(amount)),
        detection_method="d", source_dataset_ids=[],
    )


def test_higher_confidence_and_amount_scores_higher():
    low = _finding("1000", Confidence.LOW, 0.3, 0.3)
    high = _finding("100000", Confidence.HIGH, 0.9, 0.9)
    scored = score_findings([low, high])
    by_id = {f.id: f.priority_score for f in scored}
    assert by_id[high.id] > by_id[low.id]
    assert by_id[high.id] == 100.0  # top-ranked finding in the scan normalizes to 100
    assert by_id[low.id] == 0.0     # bottom-ranked normalizes to 0


def test_single_finding_scores_100():
    only = _finding("500", Confidence.MEDIUM, 0.5, 0.5)
    scored = score_findings([only])
    assert scored[0].priority_score == 100.0


def test_empty_list_returns_empty():
    assert score_findings([]) == []


def test_original_findings_not_mutated():
    f = _finding("500", Confidence.HIGH, 0.8, 0.8)
    score_findings([f])
    assert f.priority_score == 0.0  # score_findings returns copies


def test_score_detector_results_normalizes_across_the_whole_scan_not_per_detector():
    """
    Regression test: a detector that only emits one finding must not always
    score 100 regardless of how small it is next to the rest of the scan.
    """
    small = _finding("100", Confidence.LOW, 0.2, 0.2)
    huge = _finding("10000000", Confidence.HIGH, 0.9, 0.9)

    results = [
        DetectorRunResult(detector_name="A", category=LeakCategory.UNBILLED, status=DetectorStatus.RAN, findings=[small]),
        DetectorRunResult(detector_name="B", category=LeakCategory.RENEWAL, status=DetectorStatus.RAN, findings=[huge]),
    ]
    scored = score_detector_results(results)
    small_scored = scored[0].findings[0]
    huge_scored = scored[1].findings[0]

    assert huge_scored.priority_score == 100.0
    assert small_scored.priority_score == 0.0  # NOT 100 — this is the bug this test guards against
    # grouping into the original DetectorRunResult buckets is preserved
    assert scored[0].detector_name == "A"
    assert scored[1].detector_name == "B"


def test_impact_types_never_summed_together():
    findings = [
        _finding("1000", Confidence.HIGH, 0.8, 0.8, impact_type=ImpactType.POTENTIAL_LEAKAGE),
        _finding("2000", Confidence.HIGH, 0.8, 0.8, impact_type=ImpactType.AT_RISK_REVENUE),
        _finding("500", Confidence.HIGH, 0.8, 0.8, impact_type=ImpactType.POTENTIAL_LEAKAGE),
    ]
    totals = total_impact_by_type(findings)
    assert totals["POTENTIAL_LEAKAGE"]["INR"] == Decimal("1500")
    assert totals["AT_RISK_REVENUE"]["INR"] == Decimal("2000")
    assert "POTENTIAL_LEAKAGE" in totals and "AT_RISK_REVENUE" in totals
    assert len(totals) == 2  # never merged into one bucket
