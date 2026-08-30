"""
Deterministic dataset profiler. No AI involved — every signal here is a
plain heuristic over the parsed rows, computed once so the mapper and
quality scorer can build on top of it.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from dateutil import parser as dateutil_parser

from app.parsers.base import ParsedTable
from app.schemas.domain import ColumnProfile, DatasetKind, DatasetProfile

# Type inference (and the looks_like_* heuristics) only ever look at a
# bounded, evenly-spaced sample of each column's non-null values, so a
# multi-million-row file doesn't make profiling slow. Counts (non-null,
# null, distinct, duplicate rows) are exact, computed over the full column.
_MAX_TYPE_SAMPLE = 2000

_CURRENCY_SYMBOLS = ("$", "€", "£", "₹", "¥")
_CURRENCY_NAME_HINTS = (
    "amount", "price", "cost", "total", "fee", "revenue", "balance", "tax",
    "discount", "payment", "refund", "charge", "value", "fare", "rate", "due",
)
_ID_NAME_HINT_RE = re.compile(r"(?:^|[_ ])(id|no|num|number|code)(?:$|[_ ])|id$|_id$", re.IGNORECASE)
_BOOL_STRINGS = {"true", "false", "yes", "no", "y", "n"}

_KIND_KEYWORDS: dict[DatasetKind, tuple[str, ...]] = {
    DatasetKind.INVOICES: ("invoice",),
    DatasetKind.ORDERS: ("order",),
    DatasetKind.PAYMENTS: ("payment", "paid"),
    DatasetKind.CONTRACTS: ("contract", "renewal", "agreement"),
    DatasetKind.INVENTORY: ("inventory", "stock", "warehouse", "on_hand", "on hand"),
    DatasetKind.CUSTOMERS: ("customer", "client", "account"),
    DatasetKind.REFUNDS: ("refund", "return", "chargeback"),
}
_TRANSACTIONAL_KINDS = (DatasetKind.INVOICES, DatasetKind.ORDERS, DatasetKind.PAYMENTS, DatasetKind.REFUNDS)


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and v != v:  # NaN
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def _even_sample(values: list[Any], max_n: int) -> list[Any]:
    n = len(values)
    if n <= max_n:
        return values
    step = n / max_n
    return [values[int(i * step)] for i in range(max_n)]


def _to_hashable(v: Any) -> Any:
    if isinstance(v, (list, dict)):
        return str(v)
    return v


def _try_parse_date(v: Any):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        s = str(int(v)) if float(v).is_integer() else str(v)
        if len(s) != 8 or not s.isdigit():
            return None  # only entertain 8-digit numeric-as-date (e.g. YYYYMMDD)
    else:
        s = str(v).strip()
    if not s or not any(ch.isdigit() for ch in s):
        return None
    try:
        return dateutil_parser.parse(s, fuzzy=False)
    except (ValueError, OverflowError, TypeError):
        return None


def _check_date(sample: list[Any]) -> tuple[bool, float]:
    if not sample:
        return False, 0.0
    successes = sum(1 for v in sample if _try_parse_date(v) is not None)
    ratio = successes / len(sample)
    return ratio >= 0.8, round(ratio, 3)


def _check_currency(raw_name: str, sample: list[Any]) -> bool:
    if not sample:
        return False
    name_hint = any(h in raw_name.lower() for h in _CURRENCY_NAME_HINTS)

    numeric_count = 0
    symbol_hits = 0
    two_decimal_hits = 0
    for v in sample:
        s = str(v).strip()
        if any(sym in s for sym in _CURRENCY_SYMBOLS):
            symbol_hits += 1
        cleaned = s
        for sym in _CURRENCY_SYMBOLS:
            cleaned = cleaned.replace(sym, "")
        cleaned = cleaned.replace(",", "").strip()
        try:
            float(cleaned)
        except (ValueError, TypeError):
            continue
        numeric_count += 1
        if "." in cleaned and len(cleaned.split(".")[-1]) == 2:
            two_decimal_hits += 1

    if numeric_count / len(sample) < 0.8:
        return False
    symbol_ratio = symbol_hits / len(sample)
    two_decimal_ratio = two_decimal_hits / numeric_count if numeric_count else 0.0
    return name_hint or symbol_ratio > 0.3 or two_decimal_ratio > 0.6


def _check_id(raw_name: str, distinct_count: int, non_null_count: int) -> bool:
    if non_null_count == 0:
        return False
    name_hint = bool(_ID_NAME_HINT_RE.search(raw_name.lower()))
    distinct_ratio = distinct_count / non_null_count
    # 0.8 rather than a stricter ~1.0: real-world "ID" columns can still
    # contain a handful of accidental duplicates (e.g. a re-sent order) and
    # should not lose their ID classification over that alone.
    return name_hint and distinct_ratio >= 0.8


def _check_boolean(sample: list[Any]) -> bool:
    if not sample:
        return False
    lowered = set()
    for v in sample:
        if isinstance(v, bool):
            lowered.add(str(v).lower())
            continue
        lowered.add(str(v).strip().lower())
    return bool(lowered) and lowered.issubset(_BOOL_STRINGS | {"0", "1"}) and len(lowered) <= 2


def _check_integer(sample: list[Any]) -> bool:
    for v in sample:
        if isinstance(v, bool):
            return False
        if isinstance(v, int):
            continue
        if isinstance(v, float):
            if not v.is_integer():
                return False
            continue
        try:
            f = float(str(v).replace(",", ""))
        except (ValueError, TypeError):
            return False
        if not f.is_integer():
            return False
    return True


def _check_float(sample: list[Any]) -> bool:
    for v in sample:
        if isinstance(v, bool):
            return False
        if isinstance(v, (int, float)):
            continue
        try:
            float(str(v).replace(",", ""))
        except (ValueError, TypeError):
            return False
    return True


def _infer_type(
    sample: list[Any], looks_like_date: bool, looks_like_currency: bool, looks_like_id: bool
) -> Literal["string", "integer", "float", "date", "boolean", "currency", "id"]:
    if not sample:
        return "string"
    if looks_like_id:
        return "id"
    if looks_like_currency:
        return "currency"
    if looks_like_date:
        return "date"
    if _check_boolean(sample):
        return "boolean"
    if _check_integer(sample):
        return "integer"
    if _check_float(sample):
        return "float"
    return "string"


def _profile_column(raw_name: str, values: list[Any]) -> ColumnProfile:
    non_null_values = [v for v in values if not _is_missing(v)]
    non_null_count = len(non_null_values)
    null_count = len(values) - non_null_count
    distinct_count = len({_to_hashable(v) for v in non_null_values})

    sample = _even_sample(non_null_values, _MAX_TYPE_SAMPLE)
    looks_like_date, _date_ratio = _check_date(sample)
    looks_like_currency = _check_currency(raw_name, sample)
    looks_like_id = _check_id(raw_name, distinct_count, non_null_count)
    inferred_type = _infer_type(sample, looks_like_date, looks_like_currency, looks_like_id)

    return ColumnProfile(
        raw_name=raw_name,
        inferred_type=inferred_type,
        non_null_count=non_null_count,
        null_count=null_count,
        distinct_count=distinct_count,
        sample_values=non_null_values[:10],
        looks_like_currency=looks_like_currency,
        looks_like_date=looks_like_date,
        looks_like_id=looks_like_id,
    )


def _count_duplicate_rows(rows: list[dict[str, Any]]) -> int:
    """Full-row exact duplicates. Returns the number of rows beyond each
    value's first occurrence (e.g. 3 identical rows contribute 2)."""
    seen: dict[tuple, int] = {}
    for row in rows:
        try:
            key = tuple(sorted(((k, _to_hashable(v)) for k, v in row.items()), key=lambda kv: kv[0]))
        except TypeError:
            continue  # truly unhashable value even after _to_hashable; skip this row's dedup check
        seen[key] = seen.get(key, 0) + 1
    return sum(count - 1 for count in seen.values() if count > 1)


def _infer_kind(columns: list[ColumnProfile]) -> tuple[DatasetKind, float]:
    joined_names = " ".join(c.raw_name.lower() for c in columns)
    has_amount = any(c.looks_like_currency for c in columns)
    has_date = any(c.looks_like_date for c in columns)

    scores: dict[DatasetKind, float] = {}
    for kind, keywords in _KIND_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in joined_names)
        if hits == 0:
            continue
        score = hits / len(keywords)
        if kind in _TRANSACTIONAL_KINDS:
            if has_amount:
                score += 0.25
            if has_date:
                score += 0.15
        scores[kind] = min(score, 1.0)

    if not scores:
        return DatasetKind.UNKNOWN, 0.3

    best_kind = max(scores, key=lambda k: scores[k])
    best_score = scores[best_kind]
    if best_score < 0.3:
        return DatasetKind.UNKNOWN, round(1.0 - best_score, 2)
    return best_kind, round(min(best_score, 0.97), 2)


def _build_warnings(row_count: int, columns: list[ColumnProfile], duplicate_row_count: int) -> list[str]:
    warnings: list[str] = []
    if row_count == 0:
        warnings.append("Dataset contains no rows.")
        return warnings

    for col in columns:
        total = col.non_null_count + col.null_count
        if total == 0:
            continue
        null_ratio = col.null_count / total
        if null_ratio >= 0.2:
            warnings.append(f"{null_ratio * 100:.0f}% of rows are missing a value for '{col.raw_name}'.")

    if duplicate_row_count > 0:
        pct = duplicate_row_count / row_count * 100
        warnings.append(f"{duplicate_row_count} duplicate row(s) detected ({pct:.0f}% of rows are exact full-row duplicates).")

    return warnings


def profile_dataset(dataset_id: str, table: ParsedTable) -> DatasetProfile:
    row_count = len(table.rows)
    column_count = len(table.columns)

    columns: list[ColumnProfile] = []
    for col_name in table.columns:
        values = [row.get(col_name) for row in table.rows]
        columns.append(_profile_column(col_name, values))

    duplicate_row_count = _count_duplicate_rows(table.rows)
    inferred_kind, inferred_kind_confidence = _infer_kind(columns)
    warnings = list(table.warnings) + _build_warnings(row_count, columns, duplicate_row_count)

    return DatasetProfile(
        dataset_id=dataset_id,
        row_count=row_count,
        column_count=column_count,
        columns=columns,
        duplicate_row_count=duplicate_row_count,
        inferred_kind=inferred_kind,
        inferred_kind_confidence=inferred_kind_confidence,
        warnings=warnings,
    )
