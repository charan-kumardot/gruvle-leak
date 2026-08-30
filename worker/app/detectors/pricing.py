"""
PricingLeakDetector (spec section 19).

Flags customers being charged materially below the typical (median) price
for a product, where no discount field explains the gap. Deliberately
conservative: only flags underpricing (money the business could be leaving
on the table), only when it recurs for a product/customer combination
(not a one-off), and always ships with an explicit "what we don't know"
about segment/contract pricing we have no visibility into — per spec,
pricing differences are NEVER auto-classified as leakage with certainty.
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

UNDERPRICING_THRESHOLD = Decimal("0.15")   # >15% below median price/product triggers review
MIN_OCCURRENCES_TO_FLAG = 2                # a single one-off deviation is not flagged


def _median(values: list[Decimal]) -> Decimal:
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


class PricingLeakDetector(LeakDetector):
    name = "PricingLeakDetector"
    category = LeakCategory.PRICING

    def detect(self, ctx: DetectionContext) -> DetectorRunResult:
        candidate_kinds = [DatasetKind.ORDERS, DatasetKind.INVOICES]
        line_records = []
        for kind in candidate_kinds:
            line_records.extend(ctx.records_of_kind(kind))

        if not line_records:
            return self._skip(ctx, "No orders or invoices dataset was provided.")

        sample = line_records[0][1].values
        required = ["product_id", "unit_price", "quantity"]
        missing = [f for f in required if f not in sample]
        if missing:
            return self._skip(ctx, f"Line-item pricing fields not mapped: {', '.join(missing)}.")

        by_product: dict[str, list] = defaultdict(list)
        evaluated = 0
        for ds_id, rec in line_records:
            evaluated += 1
            v = rec.values
            price = to_decimal(v.get("unit_price"))
            qty = to_decimal(v.get("quantity"))
            product_id = v.get("product_id")
            if price is None or price <= 0 or qty is None or product_id is None:
                continue
            has_documented_discount = bool(v.get("discount_amount") or v.get("discount_percent"))
            by_product[str(product_id)].append((ds_id, rec.row_index, v, price, qty, has_documented_discount))

        underpriced_groups = []
        for product_id, rows in by_product.items():
            if len(rows) < MIN_OCCURRENCES_TO_FLAG:
                continue
            prices = [p for *_r, p, _q, _d in rows]
            reference_price = _median(prices)
            if reference_price <= 0:
                continue
            flagged = [
                row for row in rows
                if not row[5]  # no documented discount
                and (reference_price - row[3]) / reference_price >= UNDERPRICING_THRESHOLD
            ]
            if len(flagged) >= MIN_OCCURRENCES_TO_FLAG:
                underpriced_groups.append((product_id, reference_price, flagged))

        if not underpriced_groups:
            return DetectorRunResult(
                detector_name=self.name, category=self.category, status=DetectorStatus.RAN,
                findings=[], records_evaluated=evaluated,
            )

        findings = []
        for product_id, reference_price, flagged in underpriced_groups:
            total_gap = sum(((reference_price - p) * q for _ds, _i, _v, p, q, _d in flagged), Decimal("0"))
            currency = next((v.get("currency") for _ds, _i, v, *_r in flagged if v.get("currency")), ctx.default_currency)
            evidence = [
                evidence_from(ds_id, idx, v, ["product_id", "customer_id", "unit_price", "quantity"])
                for ds_id, idx, v, *_rest in flagged[:50]
            ]
            findings.append(LeakFinding(
                id=new_id(), scan_id=ctx.scan_id, business_id=ctx.business_id, category=self.category,
                title=f"Pricing inconsistency on product {product_id}",
                summary=(
                    f"{len(flagged)} record(s) for product {product_id} are priced at least "
                    f"{int(UNDERPRICING_THRESHOLD * 100)}% below the typical price of {currency} {reference_price}, "
                    "with no discount recorded."
                ),
                why_it_matters=(
                    "Consistent underpricing without a documented discount may mean customers are on outdated "
                    "pricing, or a pricing error is recurring — either way it's worth a manual pricing review."
                ),
                what_we_dont_know=[
                    "We could not see contract terms, customer segment, or negotiated pricing, all of which "
                    "could fully explain this gap.",
                ],
                recommended_action=f"Review pricing for product {product_id} for the affected customers and confirm whether the lower price is intentional.",
                financial_impact=FinancialImpact(
                    impact_type=ImpactType.REVENUE_OPPORTUNITY, amount=total_gap, currency=currency,
                ),
                confidence=Confidence.MEDIUM,
                confidence_explanation=(
                    f"Based on {len(flagged)} of {len(by_product[product_id])} records for this product priced "
                    "well below the observed median with no discount field set — a real pattern, but segment "
                    "or contract context that would fully explain it is not visible in the uploaded data."
                ),
                urgency=0.4, recoverability=0.4, priority_score=0.0,
                evidence=evidence,
                calculation=Calculation(
                    method="sum((median_unit_price - unit_price) * quantity) for underpriced, undiscounted records",
                    formula=f"median={currency} {reference_price}; sum over {len(flagged)} records = {currency} {total_gap}",
                    inputs={"product_id": product_id, "reference_price": str(reference_price), "flagged_count": len(flagged)},
                    result=total_gap,
                ),
                detection_method=f"Deterministic: unit_price >= {int(UNDERPRICING_THRESHOLD*100)}% below per-product median, recurring across >= {MIN_OCCURRENCES_TO_FLAG} records, no discount field set.",
                source_dataset_ids=list({ds_id for ds_id, *_ in flagged}),
            ))

        return DetectorRunResult(
            detector_name=self.name, category=self.category, status=DetectorStatus.RAN,
            findings=findings, records_evaluated=evaluated,
        )
