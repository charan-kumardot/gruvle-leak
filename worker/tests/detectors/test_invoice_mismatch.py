from decimal import Decimal

from app.detectors.invoice_mismatch import InvoiceMismatchDetector
from app.schemas.domain import DatasetKind, DetectorStatus


def test_canonical_undercharge_case_from_spec_section_78(ctx_factory):
    """Order 10,000 / invoice 8,000 -> mismatch must be exactly 2,000."""
    orders = [{"order_id": "O1", "total_amount": "10000", "currency": "INR"}]
    invoices = [{"invoice_id": "I1", "order_id": "O1", "total_amount": "8000", "currency": "INR"}]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders), ("invoices.csv", DatasetKind.INVOICES, invoices))

    result = InvoiceMismatchDetector().detect(ctx)

    assert result.status == DetectorStatus.RAN
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.financial_impact.amount == Decimal("2000")
    assert finding.calculation.result == Decimal("2000")


def test_no_finding_when_amounts_match_within_rounding_tolerance(ctx_factory):
    orders = [{"order_id": "O1", "total_amount": "100.00"}]
    invoices = [{"invoice_id": "I1", "order_id": "O1", "total_amount": "99.999"}]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders), ("invoices.csv", DatasetKind.INVOICES, invoices))
    result = InvoiceMismatchDetector().detect(ctx)
    assert result.findings == []


def test_overcharge_is_not_counted_as_leakage(ctx_factory):
    orders = [{"order_id": "O1", "total_amount": "100"}]
    invoices = [{"invoice_id": "I1", "order_id": "O1", "total_amount": "150"}]  # invoice > order
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders), ("invoices.csv", DatasetKind.INVOICES, invoices))
    result = InvoiceMismatchDetector().detect(ctx)
    assert result.findings == []


def test_duplicate_invoice_ids_flagged(ctx_factory):
    invoices = [
        {"invoice_id": "INV-1", "total_amount": "500", "currency": "INR"},
        {"invoice_id": "INV-1", "total_amount": "500", "currency": "INR"},  # duplicate
        {"invoice_id": "INV-2", "total_amount": "300", "currency": "INR"},
    ]
    ctx = ctx_factory(("invoices.csv", DatasetKind.INVOICES, invoices))
    result = InvoiceMismatchDetector().detect(ctx)

    dup_findings = [f for f in result.findings if "Duplicate" in f.title]
    assert len(dup_findings) == 1
    assert dup_findings[0].financial_impact.amount == Decimal("500")


def test_skips_without_invoices(ctx_factory):
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, [{"order_id": "O1", "total_amount": "1"}]))
    result = InvoiceMismatchDetector().detect(ctx)
    assert result.status == DetectorStatus.SKIPPED_MISSING_FIELDS
