from app.parsers.base import ParsedTable
from app.profiling.profiler import profile_dataset
from app.profiling.quality_score import compute_data_quality_score
from app.schemas.domain import CanonicalField, ColumnMapping, DataMapping, LeakCategory


def _well_formed_mapping(dataset_id: str) -> DataMapping:
    return DataMapping(
        dataset_id=dataset_id,
        mappings=[
            ColumnMapping(raw_name="order_id", canonical_field=CanonicalField.ORDER_ID, confidence=0.9, source="heuristic", reason="test"),
            ColumnMapping(raw_name="customer_id", canonical_field=CanonicalField.CUSTOMER_ID, confidence=0.9, source="heuristic", reason="test"),
            ColumnMapping(raw_name="order_date", canonical_field=CanonicalField.ORDER_DATE, confidence=0.9, source="heuristic", reason="test"),
            ColumnMapping(raw_name="total_amount", canonical_field=CanonicalField.TOTAL_AMOUNT, confidence=0.9, source="heuristic", reason="test"),
        ],
        unmapped_required_fields=[],
    )


def test_all_scores_in_valid_range_for_clean_dataset():
    rows = [
        {"order_id": f"ORD-{i}", "customer_id": f"C{i}", "order_date": "2026-01-0" + str(i % 9 + 1), "total_amount": "100.00"}
        for i in range(1, 6)
    ]
    table = ParsedTable(columns=["order_id", "customer_id", "order_date", "total_amount"], rows=rows, warnings=[])
    profile = profile_dataset("ds1", table)
    mapping = _well_formed_mapping("ds1")
    score = compute_data_quality_score(profile, mapping)

    for value in (score.overall_score, score.completeness, score.consistency, score.duplicates, score.required_fields, score.date_coverage):
        assert 0 <= value <= 100
    assert score.overall_score == round(
        (score.completeness + score.consistency + score.duplicates + score.required_fields + score.date_coverage) / 5
    )


def test_missing_customer_id_lowers_completeness_and_flags_detectors():
    rows = [
        {"order_id": "ORD-1", "customer_id": None, "order_date": "2026-01-01", "total_amount": "100.00"},
        {"order_id": "ORD-2", "customer_id": None, "order_date": "2026-01-02", "total_amount": "200.00"},
        {"order_id": "ORD-3", "customer_id": None, "order_date": "2026-01-03", "total_amount": "300.00"},
        {"order_id": "ORD-4", "customer_id": "C4", "order_date": "2026-01-04", "total_amount": "400.00"},
    ]
    table = ParsedTable(columns=["order_id", "customer_id", "order_date", "total_amount"], rows=rows, warnings=[])
    profile = profile_dataset("ds1", table)
    mapping = _well_formed_mapping("ds1")
    score = compute_data_quality_score(profile, mapping)

    assert score.completeness < 100
    assert any("customer" in e.lower() for e in score.explanations)
    assert LeakCategory.CUSTOMER in score.affected_detectors
    assert LeakCategory.UNBILLED in score.affected_detectors


def test_no_date_field_mapped_yields_zero_date_coverage():
    rows = [{"order_id": "ORD-1", "total_amount": "100.00"}]
    table = ParsedTable(columns=["order_id", "total_amount"], rows=rows, warnings=[])
    profile = profile_dataset("ds1", table)
    mapping = DataMapping(
        dataset_id="ds1",
        mappings=[
            ColumnMapping(raw_name="order_id", canonical_field=CanonicalField.ORDER_ID, confidence=0.9, source="heuristic", reason="test"),
            ColumnMapping(raw_name="total_amount", canonical_field=CanonicalField.TOTAL_AMOUNT, confidence=0.9, source="heuristic", reason="test"),
        ],
        unmapped_required_fields=[CanonicalField.ORDER_DATE],
    )
    score = compute_data_quality_score(profile, mapping)
    assert score.date_coverage == 0
    assert score.required_fields < 100


def test_duplicate_rows_lower_duplicates_score():
    rows = [
        {"order_id": "ORD-1", "total_amount": "100.00"},
        {"order_id": "ORD-1", "total_amount": "100.00"},
    ]
    table = ParsedTable(columns=["order_id", "total_amount"], rows=rows, warnings=[])
    profile = profile_dataset("ds1", table)
    mapping = DataMapping(
        dataset_id="ds1",
        mappings=[ColumnMapping(raw_name="order_id", canonical_field=CanonicalField.ORDER_ID, confidence=0.9, source="heuristic", reason="test")],
        unmapped_required_fields=[],
    )
    score = compute_data_quality_score(profile, mapping)
    assert score.duplicates < 100
    assert any("duplicate" in e.lower() for e in score.explanations)
