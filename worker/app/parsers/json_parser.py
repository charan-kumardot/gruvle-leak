"""
JSON parsing. Accepts:
  - a top-level array of objects
  - a top-level object with exactly one array-valued key (auto-detected)
  - newline-delimited JSON (NDJSON)

Flattens one level of nesting for object-valued fields (e.g.
`{"customer": {"id": 5}}` -> `customer.id`). Arrays of primitives are left
as-is; arrays of objects are JSON-stringified into the cell with a warning
(we never silently drop nested structure).

Untrusted-input note: parsed values are just data. This module never calls
eval/exec on file content and never uses any string derived from the file
to build a filesystem path.
"""
from __future__ import annotations

import json
from typing import Any

from app.parsers.base import ParsedTable


def _flatten_one_level(obj: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in obj.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat[f"{key}.{sub_key}"] = _stringify_if_needed(sub_value, f"{key}.{sub_key}", warnings)
        else:
            flat[key] = _stringify_if_needed(value, key, warnings)
    return flat


def _stringify_if_needed(value: Any, field_name: str, warnings: list[str]) -> Any:
    if isinstance(value, list):
        if value and all(isinstance(v, dict) for v in value):
            warnings.append(
                f"Field '{field_name}' contains an array of objects; it was JSON-stringified into a single cell."
            )
            return json.dumps(value, default=str)
        # Array of primitives (or empty array) — leave as-is.
        return value
    if isinstance(value, dict):
        # Nested deeper than one level — stringify rather than silently drop.
        warnings.append(f"Field '{field_name}' contains nested structure beyond one level; it was JSON-stringified.")
        return json.dumps(value, default=str)
    return value


def _records_to_table(records: list[dict[str, Any]], warnings: list[str]) -> ParsedTable:
    if not records:
        return ParsedTable(columns=[], rows=[], warnings=warnings + ["No records found in JSON."])

    flattened = []
    ordered_columns: list[str] = []
    seen = set()
    for rec in records:
        if not isinstance(rec, dict):
            warnings.append("Skipped a top-level array element that was not an object.")
            continue
        flat = _flatten_one_level(rec, warnings)
        for k in flat:
            if k not in seen:
                seen.add(k)
                ordered_columns.append(k)
        flattened.append(flat)

    rows = [{col: rec.get(col) for col in ordered_columns} for rec in flattened]
    return ParsedTable(columns=ordered_columns, rows=rows, warnings=warnings)


def _find_array_key(obj: dict[str, Any]) -> str | None:
    array_keys = [k for k, v in obj.items() if isinstance(v, list)]
    if len(array_keys) == 1:
        return array_keys[0]
    if len(array_keys) > 1:
        # Prefer the largest array-valued key if several are present, rather
        # than refusing outright.
        return max(array_keys, key=lambda k: len(obj[k]))
    return None


def _try_ndjson(text: str) -> tuple[list[dict[str, Any]] | None, list[str]]:
    warnings: list[str] = []
    records: list[dict[str, Any]] = []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None, warnings
    for i, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return None, warnings
        if not isinstance(obj, dict):
            return None, warnings
        records.append(obj)
    return records, warnings


def parse(content: bytes, filename: str) -> ParsedTable:
    warnings: list[str] = []

    if not content or not content.strip():
        return ParsedTable(columns=[], rows=[], warnings=["File is empty."])

    text = content.decode("utf-8-sig", errors="replace")
    if text.startswith("﻿"):
        text = text.lstrip("﻿")

    stripped = text.strip()
    if not stripped:
        return ParsedTable(columns=[], rows=[], warnings=["File contains no data after decoding."])

    # First try whole-document JSON (array or single object).
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None

    if parsed is not None:
        if isinstance(parsed, list):
            return _records_to_table(parsed, warnings)
        if isinstance(parsed, dict):
            array_key = _find_array_key(parsed)
            if array_key is not None:
                warnings.append(f"Top-level object had one array-valued key ('{array_key}'); using it as the record list.")
                return _records_to_table(parsed[array_key], warnings)
            # A single flat object: treat it as one record.
            warnings.append("Top-level value was a single JSON object (no array found); treated as one record.")
            return _records_to_table([parsed], warnings)
        return ParsedTable(columns=[], rows=[], warnings=[f"Top-level JSON value must be an array or object, got {type(parsed).__name__}."])

    # Fall back to NDJSON.
    ndjson_records, ndjson_warnings = _try_ndjson(stripped)
    warnings.extend(ndjson_warnings)
    if ndjson_records is not None:
        warnings.append("Parsed as newline-delimited JSON (NDJSON).")
        return _records_to_table(ndjson_records, warnings)

    return ParsedTable(columns=[], rows=[], warnings=["File is not valid JSON or NDJSON."])
