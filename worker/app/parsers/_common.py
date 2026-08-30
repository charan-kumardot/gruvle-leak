"""
Internal helpers shared by the tabular parsers (csv/xlsx). Not part of the
public parser contract — each format module still exposes its own
`parse(content, filename) -> ParsedTable`.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.parsers.base import ParsedTable


def drop_trailing_empty(df: pd.DataFrame) -> pd.DataFrame:
    """Drop fully-empty rows/columns and blank/'Unnamed' columns with no data."""
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    def _is_junk_col(col: Any) -> bool:
        name = str(col)
        return name.strip() == "" or name.startswith("Unnamed:")

    for col in list(df.columns):
        if _is_junk_col(col):
            series = df[col]
            if series.isna().all() or (series.astype(str).str.strip() == "").all():
                df = df.drop(columns=[col])
    return df


def coerce_mixed_column(series: pd.Series) -> pd.Series:
    """
    Best-effort coercion for a mixed-type object column: if the overwhelming
    majority of non-null values parse as numbers, coerce those that do and
    leave the rest untouched (never crash, never silently drop data).
    """
    if series.dtype != object:
        return series
    non_null = series.dropna()
    if non_null.empty:
        return series
    numeric = pd.to_numeric(non_null, errors="coerce")
    numeric_ratio = numeric.notna().mean()
    if numeric_ratio >= 0.9:
        coerced = pd.to_numeric(series, errors="coerce")
        return coerced.where(coerced.notna(), series)
    return series


def dedupe_columns(names: list[str]) -> list[str]:
    """Ensure column names are non-empty and unique, e.g. ['', 'a', 'a'] -> ['column_1', 'a', 'a_1']."""
    seen: dict[str, int] = {}
    result = []
    for i, name in enumerate(names):
        name = name if name else f"column_{i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        result.append(name)
    return result


def dataframe_to_table(df: pd.DataFrame, warnings: list[str]) -> ParsedTable:
    df = drop_trailing_empty(df)
    for col in df.columns:
        df[col] = coerce_mixed_column(df[col])

    columns = [str(c) for c in df.columns]
    records = df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")
    return ParsedTable(columns=columns, rows=records, warnings=warnings)
