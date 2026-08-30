"""
Turns raw parsed rows into `NormalizedRecord`s keyed by canonical field
name, using a finished `DataMapping`. Coercion is defensive: a single
field that fails to coerce on a single row never aborts the batch — it's
logged and stored as None, and every other field/row keeps processing
normally.

Money is always converted via `str(value)` first before `Decimal(...)` —
never `Decimal(float_value)` directly and never `float()` on money at
all — to avoid binary floating-point rounding artifacts entering financial
calculations downstream.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from dateutil import parser as dateutil_parser

from app.parsers.base import ParsedTable
from app.schemas.domain import CanonicalField, DataMapping, NormalizedRecord

logger = logging.getLogger("gruvle.mapping.normalize")

_CURRENCY_SYMBOLS = ("$", "€", "£", "₹", "¥")

_DATE_FIELDS = {
    CanonicalField.ORDER_DATE, CanonicalField.INVOICE_DATE, CanonicalField.DUE_DATE,
    CanonicalField.PAID_DATE, CanonicalField.RENEWAL_DATE, CanonicalField.CONTRACT_START_DATE,
    CanonicalField.CONTRACT_END_DATE, CanonicalField.REFUND_DATE, CanonicalField.LAST_MOVEMENT_DATE,
    CanonicalField.PAYMENT_DATE,
}
_DECIMAL_FIELDS = {
    CanonicalField.TOTAL_AMOUNT, CanonicalField.UNIT_PRICE, CanonicalField.LIST_PRICE,
    CanonicalField.DISCOUNT_AMOUNT, CanonicalField.COST_AMOUNT, CanonicalField.TAX_AMOUNT,
    CanonicalField.REFUND_AMOUNT, CanonicalField.PAYMENT_AMOUNT, CanonicalField.DISCOUNT_PERCENT,
}
_INTEGER_FIELDS = {CanonicalField.QUANTITY, CanonicalField.INVENTORY_QUANTITY}


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and v != v:  # NaN
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def _coerce_date(raw: Any) -> tuple[date | None, str | None]:
    if isinstance(raw, date):
        return raw, None
    try:
        parsed = dateutil_parser.parse(str(raw).strip(), fuzzy=False)
        return parsed.date(), None
    except (ValueError, OverflowError, TypeError) as e:
        return None, f"could not parse {raw!r} as a date: {e}"


def _coerce_decimal(raw: Any) -> tuple[Decimal | None, str | None]:
    if isinstance(raw, Decimal):
        return raw, None
    if isinstance(raw, bool):
        return None, f"boolean value {raw!r} cannot be coerced to a monetary/numeric amount"
    # Always go through str() first — never Decimal(float) or float(raw) —
    # so 19.99 doesn't become Decimal('19.9899999999999...').
    s = str(raw).strip()
    for sym in _CURRENCY_SYMBOLS:
        s = s.replace(sym, "")
    s = s.replace(",", "").strip()
    if s.endswith("%"):
        s = s[:-1].strip()
    if s == "":
        return None, "empty value"
    try:
        return Decimal(s), None
    except InvalidOperation:
        return None, f"could not parse {raw!r} as a decimal amount"


def _coerce_integer(raw: Any) -> tuple[int | None, str | None]:
    if isinstance(raw, bool):
        return None, f"boolean value {raw!r} cannot be coerced to an integer"
    if isinstance(raw, int):
        return raw, None
    try:
        f = float(str(raw).replace(",", "").strip())
        return int(round(f)), None
    except (ValueError, TypeError):
        return None, f"could not parse {raw!r} as an integer"


def _coerce_string(raw: Any) -> tuple[str | None, str | None]:
    return str(raw).strip(), None


def _coerce_value(canonical_field: CanonicalField, raw: Any) -> tuple[Any, str | None]:
    if _is_missing(raw):
        return None, None
    if canonical_field in _DATE_FIELDS:
        return _coerce_date(raw)
    if canonical_field in _DECIMAL_FIELDS:
        return _coerce_decimal(raw)
    if canonical_field in _INTEGER_FIELDS:
        return _coerce_integer(raw)
    return _coerce_string(raw)


def apply_mapping(dataset_id: str, table: ParsedTable, mapping: DataMapping) -> list[NormalizedRecord]:
    field_mappings = [m for m in mapping.mappings if m.canonical_field is not None]

    records: list[NormalizedRecord] = []
    for row_index, row in enumerate(table.rows):
        values: dict[str, Any] = {}
        for m in field_mappings:
            raw_value = row.get(m.raw_name)
            coerced, error = _coerce_value(m.canonical_field, raw_value)
            if error:
                logger.warning(
                    "dataset=%s row=%d field=%s (raw column %r): %s — storing None instead of failing the row.",
                    dataset_id, row_index, m.canonical_field.value, m.raw_name, error,
                )
                values[m.canonical_field.value] = None
            else:
                values[m.canonical_field.value] = coerced
        records.append(NormalizedRecord(dataset_id=dataset_id, row_index=row_index, values=values))

    return records
