"""
DiscountLeakDetector (spec section 23).

Flags discounts beyond an assumed policy ceiling. Since no business
supplies its actual discount policy in the MVP, the ceiling is an explicit,
clearly-labeled assumption (not a claim of fact) — surfaced in
`what_we_dont_know` on every finding so a user can immediately see and
challenge it.
"""
from __future__ import annotations

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

ASSUMED_POLICY_CEILING_PERCENT = Decimal("20")  # explicit, labeled assumption — see docstring


class DiscountLeakDetector(LeakDetector):
    name = "DiscountLeakDetector"
    category = LeakCategory.DISCOUNT

    def detect(self, ctx: DetectionContext) -> DetectorRunResult:
        line_records = ctx.records_of_kind(DatasetKind.ORDERS) + ctx.records_of_kind(DatasetKind.INVOICES)
        if not line_records:
            return self._skip(ctx, "No orders or invoices dataset was provided.")

        sample = line_records[0][1].values
        has_pct = "discount_percent" in sample
        has_amt = "discount_amount" in sample and ("list_price" in sample or "unit_price" in sample)
        if not (has_pct or has_amt):
            return self._skip(ctx, "No discount_percent or discount_amount field (with a price field) is mapped.")

        evaluated = 0
        flagged = []
        for ds_id, rec in line_records:
            evaluated += 1
            v = rec.values
            qty = to_decimal(v.get("quantity")) or Decimal("1")

            pct = to_decimal(v.get("discount_percent"))
            excess_amount = None

            if pct is not None and pct > ASSUMED_POLICY_CEILING_PERCENT:
                base_price = to_decimal(v.get("list_price")) or to_decimal(v.get("unit_price"))
                if base_price is not None and base_price > 0:
                    excess_pct = pct - ASSUMED_POLICY_CEILING_PERCENT
                    excess_amount = base_price * qty * (excess_pct / Decimal("100"))
            elif has_amt:
                amt = to_decimal(v.get("discount_amount"))
                base_price = to_decimal(v.get("list_price")) or to_decimal(v.get("unit_price"))
                if amt is not None and base_price is not None and base_price > 0:
                    implied_pct = (amt / (base_price * qty)) * Decimal("100") if (base_price * qty) > 0 else Decimal("0")
                    if implied_pct > ASSUMED_POLICY_CEILING_PERCENT:
                        ceiling_amount = base_price * qty * (ASSUMED_POLICY_CEILING_PERCENT / Decimal("100"))
                        excess_amount = amt - ceiling_amount

            if excess_amount is not None and excess_amount > 0:
                flagged.append((ds_id, rec.row_index, v, excess_amount))

        if not flagged:
            return DetectorRunResult(
                detector_name=self.name, category=self.category, status=DetectorStatus.RAN,
                findings=[], records_evaluated=evaluated,
            )

        total_excess = sum((a for *_r, a in flagged), Decimal("0"))
        currency = next((v.get("currency") for _ds, _i, v, _a in flagged if v.get("currency")), ctx.default_currency)
        evidence = [
            evidence_from(ds_id, idx, v, ["customer_id", "product_id", "discount_percent", "discount_amount", "unit_price"])
            for ds_id, idx, v, _a in flagged[:50]
        ]

        finding = LeakFinding(
            id=new_id(), scan_id=ctx.scan_id, business_id=ctx.business_id, category=self.category,
            title="Discounts beyond assumed policy ceiling",
            summary=(
                f"{len(flagged)} record(s) carry a discount above an assumed "
                f"{ASSUMED_POLICY_CEILING_PERCENT}% ceiling, totalling {currency} {total_excess} in excess discount."
            ),
            why_it_matters="Discounts beyond your normal policy reduce revenue on every order they touch — worth confirming these were authorized.",
            what_we_dont_know=[
                f"We assumed a {ASSUMED_POLICY_CEILING_PERCENT}% discount ceiling because no discount policy "
                "was provided. If your actual policy differs, some or all of these may be within policy.",
            ],
            recommended_action="Confirm these discounts were approved, and consider tightening discount approval controls if not.",
            financial_impact=FinancialImpact(impact_type=ImpactType.POTENTIAL_LEAKAGE, amount=total_excess, currency=currency),
            confidence=Confidence.LOW,
            confidence_explanation="Based on an assumed discount ceiling, not your actual documented policy — treat as a starting point for review, not a confirmed loss.",
            urgency=0.5, recoverability=0.6, priority_score=0.0,
            evidence=evidence,
            calculation=Calculation(
                method=f"sum(discount beyond assumed {ASSUMED_POLICY_CEILING_PERCENT}% ceiling) across flagged records",
                formula=f"sum({len(flagged)} excess-discount amounts) = {currency} {total_excess}",
                inputs={"assumed_ceiling_percent": str(ASSUMED_POLICY_CEILING_PERCENT), "flagged_count": len(flagged)},
                result=total_excess,
            ),
            detection_method=f"Deterministic: discount_percent (or implied discount from discount_amount) > {ASSUMED_POLICY_CEILING_PERCENT}%.",
            source_dataset_ids=list({ds_id for ds_id, *_ in flagged}),
        )

        return DetectorRunResult(
            detector_name=self.name, category=self.category, status=DetectorStatus.RAN,
            findings=[finding], records_evaluated=evaluated,
        )
