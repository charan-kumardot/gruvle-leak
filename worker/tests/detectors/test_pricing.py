from decimal import Decimal

from app.detectors.pricing import PricingLeakDetector
from app.schemas.domain import DatasetKind, DetectorStatus


def test_flags_recurring_underpricing_without_discount(ctx_factory):
    orders = [
        {"product_id": "P1", "unit_price": "100", "quantity": "1", "customer_id": "C1", "currency": "INR"},
        {"product_id": "P1", "unit_price": "100", "quantity": "1", "customer_id": "C2", "currency": "INR"},
        {"product_id": "P1", "unit_price": "100", "quantity": "1", "customer_id": "C3", "currency": "INR"},
        # underpriced, no discount recorded, recurs twice -> should flag
        {"product_id": "P1", "unit_price": "70", "quantity": "2", "customer_id": "C4", "currency": "INR"},
        {"product_id": "P1", "unit_price": "70", "quantity": "1", "customer_id": "C4", "currency": "INR"},
    ]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders))
    result = PricingLeakDetector().detect(ctx)

    assert result.status == DetectorStatus.RAN
    assert len(result.findings) == 1
    finding = result.findings[0]
    # median = 100; gap per unit = 30; total qty flagged = 2+1 = 3 -> 90
    assert finding.financial_impact.amount == Decimal("90")


def test_does_not_flag_underpricing_explained_by_discount(ctx_factory):
    orders = [
        {"product_id": "P1", "unit_price": "100", "quantity": "1", "customer_id": "C1"},
        {"product_id": "P1", "unit_price": "100", "quantity": "1", "customer_id": "C2"},
        {"product_id": "P1", "unit_price": "70", "quantity": "1", "customer_id": "C3", "discount_percent": "30"},
        {"product_id": "P1", "unit_price": "70", "quantity": "1", "customer_id": "C4", "discount_percent": "30"},
    ]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders))
    result = PricingLeakDetector().detect(ctx)
    assert result.findings == []


def test_one_off_deviation_not_flagged(ctx_factory):
    orders = [
        {"product_id": "P1", "unit_price": "100", "quantity": "1", "customer_id": "C1"},
        {"product_id": "P1", "unit_price": "100", "quantity": "1", "customer_id": "C2"},
        {"product_id": "P1", "unit_price": "100", "quantity": "1", "customer_id": "C3"},
        {"product_id": "P1", "unit_price": "50", "quantity": "1", "customer_id": "C4"},  # single one-off
    ]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders))
    result = PricingLeakDetector().detect(ctx)
    assert result.findings == []


def test_skips_without_required_fields(ctx_factory):
    orders = [{"product_id": "P1", "quantity": "1"}]  # no unit_price
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders))
    result = PricingLeakDetector().detect(ctx)
    assert result.status == DetectorStatus.SKIPPED_MISSING_FIELDS
