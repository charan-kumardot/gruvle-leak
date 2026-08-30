"""
RenewalLeakDetector (spec section 21).

Flags contracts already past their end date, and contracts ending within a
30-day lookahead window. Always uses AT_RISK_REVENUE, never
POTENTIAL_LEAKAGE — spec is explicit that we must never claim this revenue
is definitely lost.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from app.detectors.base import DetectionContext, LeakDetector
from app.detectors.util import evidence_from, new_id, to_decimal
from app.schemas.domain import (
    Calculation,
    Confidence,
    DatasetKind,
    DetectorRunResult,
    DetectorStatus,
    FinancialImpact,
    ImpactType,
    LeakCategory,
    LeakFinding,
)

LOOKAHEAD_DAYS = 30


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


class RenewalLeakDetector(LeakDetector):
    name = "RenewalLeakDetector"
    category = LeakCategory.RENEWAL

    def __init__(self, today: date | None = None):
        self._today = today or date.today()

    def detect(self, ctx: DetectionContext) -> DetectorRunResult:
        if not ctx.has_kind(DatasetKind.CONTRACTS):
            return self._skip(ctx, "No contracts dataset was provided.")

        contracts = ctx.records_of_kind(DatasetKind.CONTRACTS)
        sample = contracts[0][1].values if contracts else {}
        end_field = "contract_end_date" if "contract_end_date" in sample else (
            "renewal_date" if "renewal_date" in sample else None
        )
        if end_field is None:
            return self._skip(ctx, "Contracts dataset has no contract_end_date or renewal_date field mapped.")
        if "total_amount" not in sample:
            return self._skip(ctx, "Contracts dataset has no total_amount (contract value) field mapped.")

        evaluated = 0
        expiring, expired = [], []
        horizon = self._today + timedelta(days=LOOKAHEAD_DAYS)

        for ds_id, rec in contracts:
            evaluated += 1
            v = rec.values
            end_date = _as_date(v.get(end_field))
            amount = to_decimal(v.get("total_amount"))
            if end_date is None or amount is None or amount <= 0:
                continue
            if end_date < self._today:
                expired.append((ds_id, rec.row_index, v, amount, end_date))
            elif end_date <= horizon:
                expiring.append((ds_id, rec.row_index, v, amount, end_date))

        findings = []
        for label, group, title, summary_verb in (
            ("expiring", expiring, "Contracts expiring soon", f"expire within {LOOKAHEAD_DAYS} days"),
            ("expired", expired, "Contracts already past their end date", "have already passed their end date"),
        ):
            if not group:
                continue
            total = sum((a for *_r, a, _d in group), Decimal("0"))
            currency = next((v.get("currency") for _ds, _i, v, *_r in group if v.get("currency")), ctx.default_currency)
            evidence = [
                evidence_from(ds_id, idx, v, ["contract_id", "customer_id", "total_amount", end_field])
                for ds_id, idx, v, *_rest in group[:50]
            ]
            findings.append(LeakFinding(
                id=new_id(), scan_id=ctx.scan_id, business_id=ctx.business_id, category=self.category,
                title=title,
                summary=f"{len(group)} contract(s) worth {currency} {total}/year {summary_verb}.",
                why_it_matters=(
                    "Recurring revenue tied to contracts nearing or past their end date is at risk unless "
                    "renewed — this is not lost revenue yet, but it needs proactive outreach."
                ),
                what_we_dont_know=[
                    "We have no visibility into renewal conversations already in progress — some of these "
                    "may already be handled outside this data.",
                ],
                recommended_action="Prioritize renewal outreach for these accounts, starting with the highest-value contracts.",
                financial_impact=FinancialImpact(
                    impact_type=ImpactType.AT_RISK_REVENUE, amount=total, currency=currency,
                    is_recurring=True, recurrence_period="yearly",
                ),
                confidence=Confidence.HIGH if label == "expired" else Confidence.MEDIUM,
                confidence_explanation=(
                    f"Based directly on {end_field} compared to today's date ({self._today.isoformat()}) — "
                    "a reliable signal, though actual renewal likelihood varies by relationship."
                ),
                urgency=0.9 if label == "expired" else 0.7,
                recoverability=0.5, priority_score=0.0,
                evidence=evidence,
                calculation=Calculation(
                    method=f"sum(total_amount) for contracts where {end_field} {'< today' if label=='expired' else f'is within {LOOKAHEAD_DAYS} days'}",
                    formula=f"sum({len(group)} contract values) = {currency} {total}",
                    inputs={"as_of": self._today.isoformat(), "lookahead_days": LOOKAHEAD_DAYS, "count": len(group)},
                    result=total,
                ),
                detection_method=f"Deterministic date comparison against {end_field}.",
                source_dataset_ids=list({ds_id for ds_id, *_ in group}),
            ))

        return DetectorRunResult(
            detector_name=self.name, category=self.category, status=DetectorStatus.RAN,
            findings=findings, records_evaluated=evaluated,
        )
