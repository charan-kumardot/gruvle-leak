"""
Column mapper: asks the AI router for a first-pass column->canonical-field
mapping, then blends in the dataset profiler's own deterministic signals
(looks_like_currency/date/id) to adjust confidence and produce a genuinely
explanatory `reason` for every column — mapped or not.

Design note on `source` provenance: `AIProviderRouter.suggest_column_mapping`
(the public method) intentionally hides which underlying provider answered,
so a scan never fails just because one provider errored. To label
`ColumnMapping.source` truthfully (never claim "ai" when the heuristic
fallback actually produced the answer), we call the router's internal
`_try_all` dispatch, which is what `suggest_column_mapping` itself calls,
to learn which provider's name came back — we do not reimplement any AI
call ourselves, we only observe which one already-existing code path
handled it. If that internal method is ever renamed/removed, we fall back
to the public method and label conservatively as "heuristic" (the safe,
non-overclaiming default).
"""
from __future__ import annotations

import logging

from app.ai.router import build_ai_router
from app.core.config import get_settings
from app.schemas.domain import CanonicalField, ColumnMapping, DataMapping, DatasetProfile

logger = logging.getLogger("gruvle.mapping")

_CONFIDENT_THRESHOLD = 0.6

_AMOUNT_FIELDS = {
    CanonicalField.TOTAL_AMOUNT, CanonicalField.UNIT_PRICE, CanonicalField.LIST_PRICE,
    CanonicalField.DISCOUNT_AMOUNT, CanonicalField.COST_AMOUNT, CanonicalField.TAX_AMOUNT,
    CanonicalField.REFUND_AMOUNT, CanonicalField.PAYMENT_AMOUNT,
}
_DATE_FIELDS = {
    CanonicalField.ORDER_DATE, CanonicalField.INVOICE_DATE, CanonicalField.DUE_DATE,
    CanonicalField.PAID_DATE, CanonicalField.RENEWAL_DATE, CanonicalField.CONTRACT_START_DATE,
    CanonicalField.CONTRACT_END_DATE, CanonicalField.REFUND_DATE, CanonicalField.LAST_MOVEMENT_DATE,
    CanonicalField.PAYMENT_DATE,
}
_ID_FIELDS = {
    CanonicalField.CUSTOMER_ID, CanonicalField.ORDER_ID, CanonicalField.INVOICE_ID,
    CanonicalField.CONTRACT_ID, CanonicalField.PRODUCT_ID,
}

# "Required" fields per spec: total_amount specifically, plus at least one
# date field and at least one ID field from *any* of the date/id buckets
# above. Since DataMapping.unmapped_required_fields is typed as
# list[CanonicalField] (not free-text categories), a missing "date" or "id"
# bucket is represented by one fixed, documented representative member of
# that bucket (ORDER_DATE / CUSTOMER_ID) rather than a made-up new concept —
# see the note in this module's final report for why this is a reasonable
# reading of the existing schema rather than a schema change.
_DATE_BUCKET_REPRESENTATIVE = CanonicalField.ORDER_DATE
_ID_BUCKET_REPRESENTATIVE = CanonicalField.CUSTOMER_ID


async def map_columns(dataset_id: str, profile: DatasetProfile, sample_rows: list[dict]) -> DataMapping:
    router = build_ai_router(get_settings())
    raw_columns = [c.raw_name for c in profile.columns]
    canonical_fields = [f.value for f in CanonicalField]

    provider_name = "heuristic"
    try:
        ai_response, provider_name = await router._try_all(  # noqa: SLF001 - see module docstring
            "suggest_column_mapping", raw_columns, canonical_fields, sample_rows
        )
    except AttributeError:
        ai_response = await router.suggest_column_mapping(raw_columns, canonical_fields, sample_rows)

    profile_by_name = {c.raw_name: c for c in profile.columns}
    suggestion_by_name = {s.raw_name: s for s in ai_response.suggestions}
    source = "ai" if provider_name != "heuristic" else "heuristic"

    mappings: list[ColumnMapping] = []
    for raw_name in raw_columns:
        col_profile = profile_by_name.get(raw_name)
        suggestion = suggestion_by_name.get(raw_name)

        if suggestion is None:
            mappings.append(ColumnMapping(
                raw_name=raw_name,
                canonical_field=None,
                confidence=0.0,
                source="heuristic",
                reason="No mapping suggestion was returned for this column; leaving it unmapped rather than guessing.",
            ))
            continue

        canonical_field: CanonicalField | None = None
        if suggestion.canonical_field:
            try:
                canonical_field = CanonicalField(suggestion.canonical_field)
            except ValueError:
                logger.warning(
                    "AI suggested canonical_field %r for column %r outside the known vocabulary; discarding.",
                    suggestion.canonical_field, raw_name,
                )
                canonical_field = None

        confidence = max(0.0, min(1.0, suggestion.confidence))
        reason = suggestion.reason.strip() if suggestion.reason else "No reason provided by the mapping suggestion."

        if canonical_field is not None and col_profile is not None:
            if canonical_field in _AMOUNT_FIELDS and col_profile.looks_like_currency:
                confidence = min(0.99, confidence + 0.15)
                reason += f" Boosted: this column's values look like currency amounts, consistent with '{canonical_field.value}'."
            elif canonical_field in _DATE_FIELDS and col_profile.looks_like_date:
                confidence = min(0.99, confidence + 0.15)
                reason += f" Boosted: this column's values parse as dates, consistent with '{canonical_field.value}'."
            elif canonical_field in _ID_FIELDS and col_profile.looks_like_id:
                confidence = min(0.99, confidence + 0.15)
                reason += f" Boosted: this column has a high-uniqueness, ID-like value pattern, consistent with '{canonical_field.value}'."
            elif canonical_field in _AMOUNT_FIELDS and not col_profile.looks_like_currency and col_profile.inferred_type not in ("currency", "float", "integer"):
                confidence = max(0.0, confidence - 0.2)
                reason += f" Caveat: this column's values do not look numeric/currency-like, which is unusual for '{canonical_field.value}'; confidence reduced."
            elif canonical_field in _DATE_FIELDS and not col_profile.looks_like_date and col_profile.inferred_type != "date":
                confidence = max(0.0, confidence - 0.2)
                reason += f" Caveat: this column's values do not parse as dates, which is unusual for '{canonical_field.value}'; confidence reduced."
            elif canonical_field in _ID_FIELDS and not col_profile.looks_like_id:
                confidence = max(0.0, confidence - 0.1)
                reason += " Caveat: this column doesn't show the high-uniqueness pattern typical of an ID field; confidence reduced."

        mappings.append(ColumnMapping(
            raw_name=raw_name,
            canonical_field=canonical_field,
            confidence=round(confidence, 2),
            source=source,
            reason=reason,
        ))

    mapped_confident = {
        m.canonical_field for m in mappings
        if m.canonical_field is not None and m.confidence >= _CONFIDENT_THRESHOLD
    }

    unmapped_required: list[CanonicalField] = []
    if CanonicalField.TOTAL_AMOUNT not in mapped_confident:
        unmapped_required.append(CanonicalField.TOTAL_AMOUNT)
    if not (mapped_confident & _DATE_FIELDS):
        unmapped_required.append(_DATE_BUCKET_REPRESENTATIVE)
    if not (mapped_confident & _ID_FIELDS):
        unmapped_required.append(_ID_BUCKET_REPRESENTATIVE)

    return DataMapping(dataset_id=dataset_id, mappings=mappings, unmapped_required_fields=unmapped_required)
