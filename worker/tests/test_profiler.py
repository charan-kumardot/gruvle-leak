from app.parsers.base import ParsedTable
from app.profiling.profiler import profile_dataset
from app.schemas.domain import DatasetKind


def _orders_table() -> ParsedTable:
    rows = [
        {"order_id": "ORD-1", "customer_id": "C1", "order_date": "2026-01-01", "total_amount": "100.00"},
        {"order_id": "ORD-2", "customer_id": "C2", "order_date": "2026-01-02", "total_amount": "250.50"},
        {"order_id": "ORD-3", "customer_id": None, "order_date": "2026-01-03", "total_amount": "75.25"},
        {"order_id": "ORD-4", "customer_id": "C1", "order_date": "2026-01-04", "total_amount": "300.00"},
        {"order_id": "ORD-5", "customer_id": None, "order_date": "2026-01-05", "total_amount": "10.00"},
        # exact duplicate of row 4
        {"order_id": "ORD-4", "customer_id": "C1", "order_date": "2026-01-04", "total_amount": "300.00"},
    ]
    return ParsedTable(columns=["order_id", "customer_id", "order_date", "total_amount"], rows=rows, warnings=[])


def test_row_and_column_counts():
    profile = profile_dataset("ds1", _orders_table())
    assert profile.row_count == 6
    assert profile.column_count == 4


def test_detects_id_column():
    profile = profile_dataset("ds1", _orders_table())
    col = next(c for c in profile.columns if c.raw_name == "order_id")
    assert col.looks_like_id is True
    assert col.inferred_type == "id"


def test_detects_currency_column():
    profile = profile_dataset("ds1", _orders_table())
    col = next(c for c in profile.columns if c.raw_name == "total_amount")
    assert col.looks_like_currency is True
    assert col.inferred_type == "currency"


def test_detects_date_column():
    profile = profile_dataset("ds1", _orders_table())
    col = next(c for c in profile.columns if c.raw_name == "order_date")
    assert col.looks_like_date is True
    assert col.inferred_type == "date"


def test_null_counts_for_customer_id():
    profile = profile_dataset("ds1", _orders_table())
    col = next(c for c in profile.columns if c.raw_name == "customer_id")
    assert col.null_count == 2
    assert col.non_null_count == 4


def test_duplicate_row_detection():
    profile = profile_dataset("ds1", _orders_table())
    assert profile.duplicate_row_count == 1


def test_warns_about_high_null_ratio_column():
    profile = profile_dataset("ds1", _orders_table())
    assert any("customer_id" in w for w in profile.warnings)


def test_infers_orders_kind_with_confidence():
    profile = profile_dataset("ds1", _orders_table())
    assert profile.inferred_kind == DatasetKind.ORDERS
    assert 0.0 < profile.inferred_kind_confidence <= 1.0


def test_unknown_kind_for_ambiguous_columns():
    table = ParsedTable(columns=["foo", "bar"], rows=[{"foo": 1, "bar": 2}], warnings=[])
    profile = profile_dataset("ds2", table)
    assert profile.inferred_kind == DatasetKind.UNKNOWN


def test_empty_dataset_does_not_crash():
    table = ParsedTable(columns=[], rows=[], warnings=[])
    profile = profile_dataset("ds3", table)
    assert profile.row_count == 0
    assert profile.column_count == 0
    assert "no rows" in " ".join(profile.warnings).lower()


def test_type_inference_bounded_sampling_on_large_dataset():
    # 5000 rows should not be fully scanned for type inference, but the
    # profiler must still complete quickly and correctly.
    rows = [{"id": str(i), "amount": f"{i}.00"} for i in range(5000)]
    table = ParsedTable(columns=["id", "amount"], rows=rows, warnings=[])
    profile = profile_dataset("ds4", table)
    assert profile.row_count == 5000
    id_col = next(c for c in profile.columns if c.raw_name == "id")
    amount_col = next(c for c in profile.columns if c.raw_name == "amount")
    assert id_col.looks_like_id is True
    assert amount_col.looks_like_currency is True
