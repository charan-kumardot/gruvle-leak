"""
Data quality scoring. Every sub-score is 0-100 and the formula for each is
documented inline — no unexplained magic numbers. `overall_score` is the
plain average of the five sub-scores (rounded to the nearest int).
"""
from __future__ import annotations

from app.schemas.domain import CanonicalField, DataMapping, DataQualityScore, DatasetProfile, LeakCategory

_CONFIDENT_THRESHOLD = 0.6
_HIGH_NULL_RATIO_THRESHOLD = 0.10  # a mapped field missing in >=10% of rows is worth calling out

_DATE_FIELDS = {
    CanonicalField.ORDER_DATE, CanonicalField.INVOICE_DATE, CanonicalField.DUE_DATE,
    CanonicalField.PAID_DATE, CanonicalField.RENEWAL_DATE, CanonicalField.CONTRACT_START_DATE,
    CanonicalField.CONTRACT_END_DATE, CanonicalField.REFUND_DATE, CanonicalField.LAST_MOVEMENT_DATE,
    CanonicalField.PAYMENT_DATE,
}
_NUMERIC_TYPE_HINTS = {"currency", "float", "integer"}
_AMOUNT_FIELDS = {
    CanonicalField.TOTAL_AMOUNT, CanonicalField.UNIT_PRICE, CanonicalField.LIST_PRICE,
    CanonicalField.DISCOUNT_AMOUNT, CanonicalField.COST_AMOUNT, CanonicalField.TAX_AMOUNT,
    CanonicalField.REFUND_AMOUNT, CanonicalField.PAYMENT_AMOUNT,
}

# Which LeakCategory detectors a gap in a given canonical field weakens.
# Not exhaustive of every detector's inputs — a conservative, documented
# mapping of the clearest cases (e.g. spec's own example: missing
# customer_id weakens CUSTOMER and UNBILLED detectors).
_FIELD_IMPACT: dict[CanonicalField, list[LeakCategory]] = {
    CanonicalField.CUSTOMER_ID: [LeakCategory.CUSTOMER, LeakCategory.UNBILLED],
    CanonicalField.CUSTOMER_NAME: [LeakCategory.CUSTOMER],
    CanonicalField.TOTAL_AMOUNT: [LeakCategory.INVOICE, LeakCategory.PRICING, LeakCategory.UNBILLED],
    CanonicalField.INVOICE_ID: [LeakCategory.INVOICE, LeakCategory.UNBILLED],
    CanonicalField.ORDER_ID: [LeakCategory.UNBILLED, LeakCategory.OPERATIONS],
    CanonicalField.ORDER_DATE: [LeakCategory.UNBILLED, LeakCategory.OPERATIONS],
    CanonicalField.INVOICE_DATE: [LeakCategory.INVOICE, LeakCategory.RENEWAL],
    CanonicalField.DUE_DATE: [LeakCategory.INVOICE],
    CanonicalField.PAID_DATE: [LeakCategory.INVOICE],
    CanonicalField.RENEWAL_DATE: [LeakCategory.RENEWAL],
    CanonicalField.CONTRACT_START_DATE: [LeakCategory.CONTRACT],
    CanonicalField.CONTRACT_END_DATE: [LeakCategory.RENEWAL, LeakCategory.CONTRACT],
    CanonicalField.DISCOUNT_AMOUNT: [LeakCategory.DISCOUNT],
    CanonicalField.DISCOUNT_PERCENT: [LeakCategory.DISCOUNT],
    CanonicalField.LIST_PRICE: [LeakCategory.PRICING],
    CanonicalField.UNIT_PRICE: [LeakCategory.PRICING],
    CanonicalField.COST_AMOUNT: [LeakCategory.PRICING],
    CanonicalField.REFUND_AMOUNT: [LeakCategory.REFUND],
    CanonicalField.REFUND_DATE: [LeakCategory.REFUND],
    CanonicalField.INVENTORY_QUANTITY: [LeakCategory.INVENTORY],
    CanonicalField.LAST_MOVEMENT_DATE: [LeakCategory.INVENTORY],
    CanonicalField.CONTRACT_ID: [LeakCategory.CONTRACT],
    CanonicalField.PAYMENT_AMOUNT: [LeakCategory.INVOICE],
    CanonicalField.PAYMENT_DATE: [LeakCategory.INVOICE],
}

_FRIENDLY_NAMES: dict[CanonicalField, str] = {
    CanonicalField.CUSTOMER_ID: "a customer ID",
    CanonicalField.CUSTOMER_NAME: "a customer name",
    CanonicalField.TOTAL_AMOUNT: "a total amount",
    CanonicalField.INVOICE_ID: "an invoice ID",
    CanonicalField.ORDER_ID: "an order ID",
    CanonicalField.ORDER_DATE: "an order date",
    CanonicalField.INVOICE_DATE: "an invoice date",
    CanonicalField.DUE_DATE: "a due date",
    CanonicalField.PAID_DATE: "a paid date",
    CanonicalField.RENEWAL_DATE: "a renewal date",
    CanonicalField.CONTRACT_START_DATE: "a contract start date",
    CanonicalField.CONTRACT_END_DATE: "a contract end date",
    CanonicalField.DISCOUNT_AMOUNT: "a discount amount",
    CanonicalField.DISCOUNT_PERCENT: "a discount percent",
    CanonicalField.LIST_PRICE: "a list price",
    CanonicalField.UNIT_PRICE: "a unit price",
    CanonicalField.COST_AMOUNT: "a cost amount",
    CanonicalField.REFUND_AMOUNT: "a refund amount",
    CanonicalField.REFUND_DATE: "a refund date",
    CanonicalField.INVENTORY_QUANTITY: "an inventory quantity",
    CanonicalField.LAST_MOVEMENT_DATE: "a last-movement date",
    CanonicalField.CONTRACT_ID: "a contract ID",
    CanonicalField.PAYMENT_AMOUNT: "a payment amount",
    CanonicalField.PAYMENT_DATE: "a payment date",
}


def _friendly(field: CanonicalField) -> str:
    return _FRIENDLY_NAMES.get(field, field.value.replace("_", " "))


def compute_data_quality_score(profile: DatasetProfile, mapping: DataMapping) -> DataQualityScore:
    explanations: list[str] = []
    affected: set[LeakCategory] = set()

    profile_by_name = {c.raw_name: c for c in profile.columns}
    confident_mappings = [
        m for m in mapping.mappings
        if m.canonical_field is not None and m.confidence >= _CONFIDENT_THRESHOLD
    ]

    # --- completeness: mean non-null ratio across confidently-mapped fields.
    # (If nothing is confidently mapped there's nothing to judge completeness
    # of via the mapping, so we fall back to the dataset's raw non-null ratio
    # across all columns.)
    if confident_mappings:
        ratios = []
        for m in confident_mappings:
            col = profile_by_name.get(m.raw_name)
            if col is None:
                continue
            total = col.non_null_count + col.null_count
            ratios.append((col.non_null_count / total) if total else 1.0)
        completeness = round(100 * (sum(ratios) / len(ratios))) if ratios else 100
    else:
        ratios = []
        for col in profile.columns:
            total = col.non_null_count + col.null_count
            ratios.append((col.non_null_count / total) if total else 1.0)
        completeness = round(100 * (sum(ratios) / len(ratios))) if ratios else 100

    # --- consistency: fraction of confidently-mapped fields whose inferred
    # type is compatible with what that canonical field expects (date fields
    # should look like dates, amount fields should look numeric/currency).
    # 100 when there's nothing mapped to judge.
    if confident_mappings:
        compatible = 0
        for m in confident_mappings:
            col = profile_by_name.get(m.raw_name)
            if col is None:
                continue
            if m.canonical_field in _DATE_FIELDS:
                ok = col.looks_like_date or col.inferred_type == "date"
            elif m.canonical_field in _AMOUNT_FIELDS:
                ok = col.looks_like_currency or col.inferred_type in _NUMERIC_TYPE_HINTS
            else:
                ok = True  # no strong type expectation to violate
            compatible += 1 if ok else 0
        consistency = round(100 * compatible / len(confident_mappings))
    else:
        consistency = 100

    # --- duplicates: percentage of rows that are NOT exact full-row duplicates.
    if profile.row_count > 0:
        duplicates = round(100 * (1 - min(1.0, profile.duplicate_row_count / profile.row_count)))
    else:
        duplicates = 100

    # --- required_fields: of the (up to) 3 tracked essential buckets
    # (total_amount / any date field / any ID field — see mapper.py), how
    # many are confidently mapped.
    total_buckets = 3
    required_fields = round(100 * (1 - len(mapping.unmapped_required_fields) / total_buckets))

    # --- date_coverage: mean non-null ratio across confidently-mapped date
    # fields. 0 if no date field is confidently mapped at all — time-based
    # detectors (renewal, aging, unbilled-by-date) simply cannot run.
    date_mappings = [m for m in confident_mappings if m.canonical_field in _DATE_FIELDS]
    if date_mappings:
        ratios = []
        for m in date_mappings:
            col = profile_by_name.get(m.raw_name)
            if col is None:
                continue
            total = col.non_null_count + col.null_count
            ratios.append((col.non_null_count / total) if total else 1.0)
        date_coverage = round(100 * (sum(ratios) / len(ratios))) if ratios else 0
    else:
        date_coverage = 0

    overall = round((completeness + consistency + duplicates + required_fields + date_coverage) / 5)

    # --- explanations: one per confidently-mapped field with a non-trivial
    # null rate, plus one per missing required bucket, plus duplicates.
    for m in confident_mappings:
        col = profile_by_name.get(m.raw_name)
        if col is None:
            continue
        total = col.non_null_count + col.null_count
        if total == 0:
            continue
        null_ratio = col.null_count / total
        if null_ratio >= _HIGH_NULL_RATIO_THRESHOLD:
            pct = round(null_ratio * 100)
            explanations.append(
                f"{pct}% of rows do not contain {_friendly(m.canonical_field)} (column '{m.raw_name}'). "
                f"Some leakage checks may be incomplete."
            )
            affected.update(_FIELD_IMPACT.get(m.canonical_field, []))

    for field in mapping.unmapped_required_fields:
        explanations.append(
            f"No confident mapping was found for {_friendly(field)}. Detectors that depend on it may be skipped entirely."
        )
        affected.update(_FIELD_IMPACT.get(field, []))

    if profile.duplicate_row_count > 0 and profile.row_count > 0:
        pct = round(100 * profile.duplicate_row_count / profile.row_count)
        explanations.append(
            f"{profile.duplicate_row_count} rows ({pct}%) are exact full-row duplicates, "
            f"which can inflate totals if not deduplicated before analysis."
        )

    return DataQualityScore(
        overall_score=overall,
        completeness=completeness,
        consistency=consistency,
        duplicates=duplicates,
        required_fields=required_fields,
        date_coverage=date_coverage,
        explanations=explanations,
        affected_detectors=sorted(affected, key=lambda c: c.value),
    )
