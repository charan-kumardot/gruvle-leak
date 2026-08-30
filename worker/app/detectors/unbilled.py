"""
UnbilledRevenueDetector (spec section 18).

Finds completed orders that have no matching invoice. Requires an ORDERS
dataset with order_id + status + total_amount, and an INVOICES dataset
whose records carry order_id (a direct, reliable join key) — if invoices
don't reference order_id, we cannot safely claim "no matching invoice"
without risking a false positive, so the detector skips with a clear reason
rather than guessing.
"""
from __future__ import annotations

from decimal import Decimal

from app.detectors.base import DetectionContext, LeakDetector
from app.detectors.util import evidence_from, is_completed_status, new_id, to_decimal
from app.schemas.domain import (
    Calculation,
    Confidence,
    DatasetKind,
    DetectorRunResult,
    DetectorStatus,
    EvidenceRecordRef,
    FinancialImpact,
    ImpactType,
    LeakCategory,
    LeakFinding,
)


class UnbilledRevenueDetector(LeakDetector):
    name = "UnbilledRevenueDetector"
    category = LeakCategory.UNBILLED

    def detect(self, ctx: DetectionContext) -> DetectorRunResult:
        if not ctx.has_kind(DatasetKind.ORDERS):
            return self._skip(ctx, "No orders dataset was provided, so unbilled work cannot be checked.")
        if not ctx.has_kind(DatasetKind.INVOICES):
            return self._skip(
                ctx, "No invoice dataset was provided, so we cannot confirm which completed orders are unbilled."
            )

        orders = ctx.records_of_kind(DatasetKind.ORDERS)
        invoices = ctx.records_of_kind(DatasetKind.INVOICES)

        sample_order = orders[0][1].values if orders else {}
        sample_invoice = invoices[0][1].values if invoices else {}
        for required in ("order_id", "status", "total_amount"):
            if required not in sample_order:
                return self._skip(ctx, f"Orders dataset is missing a mapped '{required}' field.")
        if "order_id" not in sample_invoice:
            return self._skip(
                ctx,
                "Invoices dataset has no order_id field mapped, so orders cannot be reliably matched to invoices.",
            )

        invoiced_order_ids: set[str] = set()
        for _, inv in invoices:
            oid = inv.values.get("order_id")
            if oid is not None:
                invoiced_order_ids.add(str(oid).strip())

        unbilled: list[tuple[str, int, dict, Decimal]] = []
        evaluated = 0
        for dataset_id, order in orders:
            evaluated += 1
            values = order.values
            if not is_completed_status(values.get("status")):
                continue
            order_id = values.get("order_id")
            if order_id is None or str(order_id).strip() in invoiced_order_ids:
                continue
            amount = to_decimal(values.get("total_amount"))
            if amount is None or amount <= 0:
                continue
            unbilled.append((dataset_id, order.row_index, values, amount))

        if not unbilled:
            return DetectorRunResult(
                detector_name=self.name, category=self.category, status=DetectorStatus.RAN,
                findings=[], records_evaluated=evaluated,
            )

        total = sum((amt for *_rest, amt in unbilled), Decimal("0"))
        currency = next(
            (v.get("currency") for *_r, v, _a in unbilled if v.get("currency")), ctx.default_currency
        )

        evidence: list[EvidenceRecordRef] = [
            evidence_from(ds_id, idx, values, ["order_id", "customer_id", "status", "total_amount", "order_date"])
            for ds_id, idx, values, _amt in unbilled[:50]  # cap displayed evidence; total count still accurate
        ]

        finding = LeakFinding(
            id=new_id(),
            scan_id=ctx.scan_id,
            business_id=ctx.business_id,
            category=self.category,
            title="Potential unbilled revenue",
            summary=(
                f"{len(unbilled)} completed order(s) totalling {currency} {total} have no matching invoice."
            ),
            why_it_matters=(
                "These orders were marked completed but we found no invoice referencing them. If work was "
                "delivered but never billed, this revenue may never be collected unless invoiced."
            ),
            what_we_dont_know=[
                "We matched orders to invoices only by order_id — if your invoicing system uses a different "
                "reference, some of these may already be billed under a record we couldn't match.",
            ],
            recommended_action="Review these orders and issue invoices for any that were genuinely completed but never billed.",
            financial_impact=FinancialImpact(
                impact_type=ImpactType.POTENTIAL_LEAKAGE, amount=total, currency=currency, is_recurring=False,
            ),
            confidence=Confidence.HIGH,
            confidence_explanation=(
                f"{len(unbilled)} completed orders were matched against {len(invoices)} invoice records by "
                "order_id with no corresponding invoice found — a direct, reliable join."
            ),
            urgency=0.8,
            recoverability=0.9,
            priority_score=0.0,  # set later by app/scoring/priority.py
            evidence=evidence,
            calculation=Calculation(
                method="sum(total_amount) for completed orders with no matching invoice.order_id",
                formula=f"sum({len(unbilled)} order totals) = {currency} {total}",
                inputs={"unbilled_order_count": len(unbilled), "invoice_count": len(invoices)},
                result=total,
            ),
            detection_method="Deterministic join: ORDERS.order_id not in INVOICES.order_id, filtered to completed status.",
            source_dataset_ids=list({ds_id for ds_id, *_ in unbilled} | {ds_id for ds_id, _ in invoices}),
        )

        return DetectorRunResult(
            detector_name=self.name, category=self.category, status=DetectorStatus.RAN,
            findings=[finding], records_evaluated=evaluated,
        )
