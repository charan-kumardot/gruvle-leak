"""
Deterministic leak priority scoring (spec section 28).

priority = financial_impact x confidence x urgency x recoverability,
normalized to 0-100 across the findings in a single scan.

This is pure arithmetic — no AI involved, ever. financial_impact is
log-scaled before normalizing so one very large finding doesn't crush every
other finding's score to near-zero (log-then-normalize is what preserves
ranking across a real spread of amounts within one scan, per manual testing
of the raw-amount x confidence x urgency x recoverability formula, which
produced ratios of >1000:1 between the top and second finding in normal
data whenever a single large unbilled-revenue finding was present).
"""
from __future__ import annotations

import math
from decimal import Decimal

from app.schemas.domain import Confidence, DetectorRunResult, LeakFinding

_CONFIDENCE_WEIGHT = {
    Confidence.HIGH: 1.0,
    Confidence.MEDIUM: 0.6,
    Confidence.LOW: 0.3,
}


def _log_amount(finding: LeakFinding) -> float:
    amount = float(finding.financial_impact.amount)
    return math.log1p(max(amount, 0.0))


def score_findings(findings: list[LeakFinding]) -> list[LeakFinding]:
    """Returns new LeakFinding objects with `priority_score` populated (0-100). Input list order preserved."""
    if not findings:
        return []

    raw_scores = []
    log_amounts = [_log_amount(f) for f in findings]
    min_log, max_log = min(log_amounts), max(log_amounts)
    log_range = (max_log - min_log) or 1.0

    for finding, log_amt in zip(findings, log_amounts):
        amount_norm = (log_amt - min_log) / log_range  # 0..1 within this scan
        confidence_w = _CONFIDENCE_WEIGHT[finding.confidence]
        raw = amount_norm * confidence_w * finding.urgency * finding.recoverability
        raw_scores.append(raw)

    min_raw, max_raw = min(raw_scores), max(raw_scores)
    raw_range = (max_raw - min_raw) or 1.0

    scored = []
    for finding, raw in zip(findings, raw_scores):
        normalized = (raw - min_raw) / raw_range if len(findings) > 1 else 1.0
        priority = round(normalized * 100, 1)
        scored.append(finding.model_copy(update={"priority_score": priority}))

    return scored


def score_detector_results(results: list[DetectorRunResult]) -> list[DetectorRunResult]:
    """
    Scores findings across the ENTIRE scan at once, then reassigns them back
    into their original DetectorRunResult groupings. Scoring per-detector
    instead of per-scan is a bug: a detector that only ever emits one or two
    findings would have every one of them normalize straight to 100,
    regardless of how it compares to the rest of the scan.
    """
    flat = [f for r in results for f in r.findings]
    scored_by_id = {f.id: f for f in score_findings(flat)}

    out = []
    for r in results:
        out.append(r.model_copy(update={"findings": [scored_by_id[f.id] for f in r.findings]}))
    return out


def total_impact_by_type(findings: list[LeakFinding]) -> dict[str, dict[str, Decimal]]:
    """
    Sums financial impact grouped by (impact_type, currency) — never combined
    across types (spec section 34: potential leakage, at-risk revenue,
    revenue opportunity, and capital tied up must never be summed together).
    """
    totals: dict[str, dict[str, Decimal]] = {}
    for f in findings:
        key = f.financial_impact.impact_type.value
        currency = f.financial_impact.currency
        totals.setdefault(key, {})
        totals[key][currency] = totals[key].get(currency, Decimal("0")) + f.financial_impact.amount
    return totals
