"""
Tests for app.mapping.mapper and app.mapping.normalize.

`get_settings` is monkeypatched to return a Settings object with no AI keys
configured, so `map_columns` deterministically exercises the offline
heuristic path (no network calls, no dependency on real API keys that may
happen to be present in the local .env during development).
"""
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.mapping import mapper
from app.mapping.normalize import apply_mapping
from app.parsers.base import ParsedTable
from app.profiling.profiler import profile_dataset
from app.schemas.domain import CanonicalField, DataMapping, ColumnMapping


@pytest.fixture(autouse=True)
def _no_ai_keys(monkeypatch):
    monkeypatch.setattr(mapper, "get_settings", lambda: Settings(
        gemini_api_key="", groq_api_key="", openrouter_api_key="",
        _env_file=None,
    ))


def _sample_table() -> ParsedTable:
    rows = [
        {"Invoice Total": "100.00", "Customer ID": "C1", "Invoice Date": "2026-01-01", "Widget Flavor": "n/a"},
        {"Invoice Total": "250.50", "Customer ID": "C2", "Invoice Date": "2026-01-02", "Widget Flavor": "urgent"},
        {"Invoice Total": "75.25", "Customer ID": "C3", "Invoice Date": "2026-01-03", "Widget Flavor": ""},
        {"Invoice Total": "300.00", "Customer ID": "C4", "Invoice Date": "2026-01-04", "Widget Flavor": "vip"},
    ]
    return ParsedTable(
        columns=["Invoice Total", "Customer ID", "Invoice Date", "Widget Flavor"],
        rows=rows,
        warnings=[],
    )


@pytest.mark.asyncio
async def test_obvious_columns_map_confidently():
    table = _sample_table()
    profile = profile_dataset("ds1", table)
    mapping = await mapper.map_columns("ds1", profile, table.rows[:3])

    by_raw = {m.raw_name: m for m in mapping.mappings}
    assert by_raw["Invoice Total"].canonical_field == CanonicalField.TOTAL_AMOUNT
    assert by_raw["Invoice Total"].confidence >= 0.6
    assert by_raw["Invoice Total"].reason  # non-empty, explanatory

    assert by_raw["Customer ID"].canonical_field == CanonicalField.CUSTOMER_ID
    assert by_raw["Customer ID"].confidence >= 0.6

    assert by_raw["Invoice Date"].canonical_field == CanonicalField.INVOICE_DATE
    assert by_raw["Invoice Date"].confidence >= 0.6


@pytest.mark.asyncio
async def test_ambiguous_column_left_unmapped_or_low_confidence():
    table = _sample_table()
    profile = profile_dataset("ds1", table)
    mapping = await mapper.map_columns("ds1", profile, table.rows[:3])

    by_raw = {m.raw_name: m for m in mapping.mappings}
    notes = by_raw["Widget Flavor"]
    assert notes.canonical_field is None or notes.confidence < 0.6


@pytest.mark.asyncio
async def test_every_mapping_has_a_source_and_reason():
    table = _sample_table()
    profile = profile_dataset("ds1", table)
    mapping = await mapper.map_columns("ds1", profile, table.rows[:3])
    for m in mapping.mappings:
        assert m.source in ("heuristic", "ai", "user")
        assert isinstance(m.reason, str) and m.reason.strip()


@pytest.mark.asyncio
async def test_confident_currency_mapping_gets_profile_boost_reason():
    table = _sample_table()
    profile = profile_dataset("ds1", table)
    mapping = await mapper.map_columns("ds1", profile, table.rows[:3])
    by_raw = {m.raw_name: m for m in mapping.mappings}
    assert "currency" in by_raw["Invoice Total"].reason.lower() or "Boosted" in by_raw["Invoice Total"].reason


@pytest.mark.asyncio
async def test_unmapped_required_fields_when_essentials_missing():
    table = ParsedTable(
        columns=["Notes", "Misc"],
        rows=[{"Notes": "a", "Misc": "b"}],
        warnings=[],
    )
    profile = profile_dataset("ds2", table)
    mapping = await mapper.map_columns("ds2", profile, table.rows)
    assert CanonicalField.TOTAL_AMOUNT in mapping.unmapped_required_fields
    assert len(mapping.unmapped_required_fields) == 3  # amount + date bucket + id bucket


@pytest.mark.asyncio
async def test_required_fields_satisfied_when_essentials_present():
    table = _sample_table()
    profile = profile_dataset("ds1", table)
    mapping = await mapper.map_columns("ds1", profile, table.rows[:3])
    assert mapping.unmapped_required_fields == []


# --- apply_mapping / normalize.py -----------------------------------------

def test_apply_mapping_coerces_dates_and_decimal_amounts():
    table = _sample_table()
    mapping = DataMapping(
        dataset_id="ds1",
        mappings=[
            ColumnMapping(raw_name="Invoice Total", canonical_field=CanonicalField.TOTAL_AMOUNT, confidence=0.9, source="heuristic", reason="test"),
            ColumnMapping(raw_name="Customer ID", canonical_field=CanonicalField.CUSTOMER_ID, confidence=0.9, source="heuristic", reason="test"),
            ColumnMapping(raw_name="Invoice Date", canonical_field=CanonicalField.INVOICE_DATE, confidence=0.9, source="heuristic", reason="test"),
            ColumnMapping(raw_name="Notes", canonical_field=None, confidence=0.0, source="heuristic", reason="test"),
        ],
        unmapped_required_fields=[],
    )
    records = apply_mapping("ds1", table, mapping)
    assert len(records) == 4
    first = records[0]
    assert first.values["total_amount"] == Decimal("100.00")
    assert isinstance(first.values["total_amount"], Decimal)
    assert str(first.values["invoice_date"]) == "2026-01-01"
    assert first.values["customer_id"] == "C1"
    assert "notes" not in first.values  # unmapped columns are not included


def test_apply_mapping_never_uses_float_for_money():
    # 19.1 has no exact binary float representation; Decimal(str(19.1))
    # must equal Decimal("19.1") exactly, unlike Decimal(19.1).
    table = ParsedTable(columns=["price"], rows=[{"price": 19.1}], warnings=[])
    mapping = DataMapping(
        dataset_id="ds1",
        mappings=[ColumnMapping(raw_name="price", canonical_field=CanonicalField.UNIT_PRICE, confidence=0.9, source="heuristic", reason="test")],
        unmapped_required_fields=[],
    )
    records = apply_mapping("ds1", table, mapping)
    assert records[0].values["unit_price"] == Decimal("19.1")


def test_apply_mapping_skips_bad_value_without_crashing_batch():
    table = ParsedTable(
        columns=["total"],
        rows=[{"total": "not a number"}, {"total": "50.00"}],
        warnings=[],
    )
    mapping = DataMapping(
        dataset_id="ds1",
        mappings=[ColumnMapping(raw_name="total", canonical_field=CanonicalField.TOTAL_AMOUNT, confidence=0.9, source="heuristic", reason="test")],
        unmapped_required_fields=[],
    )
    records = apply_mapping("ds1", table, mapping)
    assert len(records) == 2
    assert records[0].values["total_amount"] is None
    assert records[1].values["total_amount"] == Decimal("50.00")
