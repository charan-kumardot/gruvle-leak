from decimal import Decimal

from app.detectors.unbilled import UnbilledRevenueDetector
from app.schemas.domain import DatasetKind, DetectorStatus, ImpactType


def test_flags_completed_order_with_no_invoice(ctx_factory):
    orders = [
        {"order_id": "ORDER-101", "status": "Completed", "total_amount": "25000", "currency": "INR", "customer_id": "C1"},
        {"order_id": "ORDER-102", "status": "Completed", "total_amount": "10000", "currency": "INR", "customer_id": "C2"},
        {"order_id": "ORDER-103", "status": "Pending", "total_amount": "5000", "currency": "INR", "customer_id": "C3"},
    ]
    invoices = [
        {"invoice_id": "INV-1", "order_id": "ORDER-102", "total_amount": "10000", "currency": "INR"},
    ]
    ctx = ctx_factory(
        ("orders.csv", DatasetKind.ORDERS, orders),
        ("invoices.csv", DatasetKind.INVOICES, invoices),
    )
    result = UnbilledRevenueDetector().detect(ctx)

    assert result.status == DetectorStatus.RAN
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.financial_impact.impact_type == ImpactType.POTENTIAL_LEAKAGE
    assert finding.financial_impact.amount == Decimal("25000")
    assert finding.financial_impact.currency == "INR"
    assert len(finding.evidence) == 1
    assert finding.evidence[0].display_fields["order_id"] == "ORDER-101"


def test_no_finding_when_all_completed_orders_invoiced(ctx_factory):
    orders = [{"order_id": "O1", "status": "completed", "total_amount": "500", "currency": "INR"}]
    invoices = [{"invoice_id": "I1", "order_id": "O1", "total_amount": "500", "currency": "INR"}]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders), ("invoices.csv", DatasetKind.INVOICES, invoices))
    result = UnbilledRevenueDetector().detect(ctx)
    assert result.status == DetectorStatus.RAN
    assert result.findings == []


def test_skips_without_invoices_dataset(ctx_factory):
    orders = [{"order_id": "O1", "status": "completed", "total_amount": "500"}]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders))
    result = UnbilledRevenueDetector().detect(ctx)
    assert result.status == DetectorStatus.SKIPPED_MISSING_FIELDS
    assert "invoice" in result.skip_reason.lower()


def test_skips_when_invoices_lack_order_id(ctx_factory):
    orders = [{"order_id": "O1", "status": "completed", "total_amount": "500"}]
    invoices = [{"invoice_id": "I1", "total_amount": "500"}]  # no order_id field mapped
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders), ("invoices.csv", DatasetKind.INVOICES, invoices))
    result = UnbilledRevenueDetector().detect(ctx)
    assert result.status == DetectorStatus.SKIPPED_MISSING_FIELDS


def test_ignores_non_completed_and_zero_amount_orders(ctx_factory):
    orders = [
        {"order_id": "O1", "status": "cancelled", "total_amount": "1000"},
        {"order_id": "O2", "status": "completed", "total_amount": "0"},
    ]
    invoices = [{"invoice_id": "I1", "order_id": "OTHER", "total_amount": "1"}]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders), ("invoices.csv", DatasetKind.INVOICES, invoices))
    result = UnbilledRevenueDetector().detect(ctx)
    assert result.findings == []
