"""
InvoiceMismatchDetector (spec section 20).

Two independent checks, each producing its own finding when evidence exists:
1. Order-vs-invoice undercharge: invoice total_amount < matching order
   total_amount. This is the canonical deterministic test case from spec
   section 78 (order 10,000 / invoice 8,000 -> mismatch 2,000).
2. Duplicate invoices: more than one invoice record sharing the same
   invoice_id.

We only count *undercharges* as leaked revenue. An invoice greater than its
order (overcharge) is a data-quality anomaly worth surfacing to the user
elsewhere, not revenue the business is losing, so it is deliberately
excluded from the financial_impact total here.
"""
from __future__ import annotations

from collections import defaultdict
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

# Amounts within this tolerance are treated as equal (rounding noise, not a mismatch).
ROUNDING_TOLERANCE = Decimal("0.01")


class InvoiceMismatchDetector(LeakDetector):
    name = "InvoiceMismatchDetector"
    category = LeakCategory.INVOICE

    def detect(self, ctx: DetectionContext) -> DetectorRunResult:
        if not ctx.has_kind(DatasetKind.INVOICES):
            return self._skip(ctx, "No invoice dataset was provided.")

        invoices = ctx.records_of_kind(DatasetKind.INVOICES)
        sample_invoice = invoices[0][1].values if invoices else {}
        if "total_amount" not in sample_invoice:
            return self._skip(ctx, "Invoices dataset is missing a mapped 'total_amount' field.")

        findings: list[LeakFinding] = []
        evaluated = len(invoices)

        # --- Check 1: undercharge vs. matching order ---
        if ctx.has_kind(DatasetKind.ORDERS) and "order_id" in sample_invoice:
            orders = ctx.records_of_kind(DatasetKind.ORDERS)
            sample_order = orders[0][1].values if orders else {}
            if "order_id" in sample_order and "total_amount" in sample_order:
                order_totals: dict[str, Decimal] = {}
                for _, order in orders:
                    oid = order.values.get("order_id")
                    amt = to_decimal(order.values.get("total_amount"))
                    if oid is not None and amt is not None:
                        order_totals[str(oid).strip()] = amt

                undercharges = []
                for ds_id, inv in invoices:
                    oid = inv.values.get("order_id")
                    if oid is None:
                        continue
                    order_amt = order_totals.get(str(oid).strip())
                    if order_amt is None:
                        continue
                    inv_amt = to_decimal(inv.values.get("total_amount"))
                    if inv_amt is None:
                        continue
                    delta = order_amt - inv_amt
                    if delta > ROUNDING_TOLERANCE:
                        undercharges.append((ds_id, inv.row_index, inv.values, order_amt, inv_amt, delta))

                if undercharges:
                    total_delta = sum((d for *_r, d in undercharges), Decimal("0"))
                    currency = next(
                        (v.get("currency") for _d, _i, v, *_r in undercharges if v.get("currency")),
                        ctx.default_currency,
                    )
                    evidence = [
                        evidence_from(ds_id, idx, values, ["invoice_id", "order_id", "total_amount", "customer_id"])
                        for ds_id, idx, values, *_rest in undercharges[:50]
                    ]
                    findings.append(LeakFinding(
                        id=new_id(), scan_id=ctx.scan_id, business_id=ctx.business_id, category=self.category,
                        title="Invoice amounts below matching order value",
                        summary=(
                            f"{len(undercharges)} invoice(s) total {currency} {total_delta} less than their "
                            f"matching order value."
                        ),
                        why_it_matters=(
                            "When an invoice is billed for less than the order it corresponds to, the "
                            "difference is revenue that was never captured unless a documented discount "
                            "explains the gap."
                        ),
                        what_we_dont_know=[
                            "We could not confirm whether an approved discount or credit explains each gap — "
                            "review before treating this as billing error.",
                        ],
                        recommended_action="Review these order/invoice pairs and issue a supplementary invoice if the gap is unexplained.",
                        financial_impact=FinancialImpact(
                            impact_type=ImpactType.POTENTIAL_LEAKAGE, amount=total_delta, currency=currency,
                        ),
                        confidence=Confidence.HIGH,
                        confidence_explanation=(
                            f"{len(undercharges)} invoices were matched 1:1 to orders by order_id with an "
                            "invoice total strictly below the order total — direct arithmetic, not inference."
                        ),
                        urgency=0.7, recoverability=0.8, priority_score=0.0,
                        evidence=evidence,
                        calculation=Calculation(
                            method="sum(order.total_amount - invoice.total_amount) where positive, matched by order_id",
                            formula=f"sum({len(undercharges)} deltas) = {currency} {total_delta}",
                            inputs={"mismatched_pair_count": len(undercharges)},
                            result=total_delta,
                        ),
                        detection_method="Deterministic 1:1 join on order_id; delta = order.total_amount - invoice.total_amount.",
                        source_dataset_ids=list({ds_id for ds_id, *_ in undercharges}),
                    ))

        # --- Check 2: duplicate invoice_id ---
        if "invoice_id" in sample_invoice:
            groups: dict[str, list] = defaultdict(list)
            for ds_id, inv in invoices:
                iid = inv.values.get("invoice_id")
                if iid is not None:
                    groups[str(iid).strip()].append((ds_id, inv))

            duplicate_extra_records = []
            for iid, group in groups.items():
                if len(group) > 1:
                    # keep the first occurrence as "original", the rest as the duplicate anomaly
                    duplicate_extra_records.extend(group[1:])

            if duplicate_extra_records:
                amounts = [to_decimal(inv.values.get("total_amount")) or Decimal("0") for _ds, inv in duplicate_extra_records]
                total_dup = sum(amounts, Decimal("0"))
                currency = next(
                    (inv.values.get("currency") for _ds, inv in duplicate_extra_records if inv.values.get("currency")),
                    ctx.default_currency,
                )
                evidence = [
                    evidence_from(ds_id, inv.row_index, inv.values, ["invoice_id", "total_amount", "customer_id", "invoice_date"])
                    for ds_id, inv in duplicate_extra_records[:50]
                ]
                findings.append(LeakFinding(
                    id=new_id(), scan_id=ctx.scan_id, business_id=ctx.business_id, category=self.category,
                    title="Duplicate invoice records",
                    summary=f"{len(duplicate_extra_records)} invoice record(s) share an invoice_id already used by another record.",
                    why_it_matters=(
                        "Duplicate invoice records can mean a customer was billed twice, or that revenue is "
                        "being double-counted in your reporting — either way it needs manual reconciliation."
                    ),
                    what_we_dont_know=[
                        "We flagged duplicates by exact invoice_id match only — this doesn't tell us whether "
                        "the customer was actually charged twice or if this is a data-entry duplicate.",
                    ],
                    recommended_action="Reconcile these invoice_id duplicates against your billing system before assuming double billing.",
                    financial_impact=FinancialImpact(
                        impact_type=ImpactType.POTENTIAL_LEAKAGE, amount=total_dup, currency=currency,
                    ),
                    confidence=Confidence.MEDIUM,
                    confidence_explanation="Exact invoice_id duplication is a strong signal but requires human confirmation of intent.",
                    urgency=0.6, recoverability=0.7, priority_score=0.0,
                    evidence=evidence,
                    calculation=Calculation(
                        method="sum(total_amount) for invoice records beyond the first occurrence of each invoice_id",
                        formula=f"sum({len(duplicate_extra_records)} duplicate records) = {currency} {total_dup}",
                        inputs={"duplicate_record_count": len(duplicate_extra_records)},
                        result=total_dup,
                    ),
                    detection_method="Deterministic grouping by invoice_id; groups with count > 1 flagged beyond the first record.",
                    source_dataset_ids=list({ds_id for ds_id, _ in duplicate_extra_records}),
                ))

        return DetectorRunResult(
            detector_name=self.name, category=self.category, status=DetectorStatus.RAN,
            findings=findings, records_evaluated=evaluated,
        )
