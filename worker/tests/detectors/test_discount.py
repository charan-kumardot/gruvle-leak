from decimal import Decimal

from app.detectors.discount import DiscountLeakDetector
from app.schemas.domain import DatasetKind, DetectorStatus


def test_flags_discount_above_assumed_ceiling_by_percent(ctx_factory):
    orders = [
        {"customer_id": "C1", "product_id": "P1", "unit_price": "1000", "quantity": "1", "discount_percent": "40", "currency": "INR"},
        {"customer_id": "C2", "product_id": "P1", "unit_price": "1000", "quantity": "1", "discount_percent": "10", "currency": "INR"},
    ]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders))
    result = DiscountLeakDetector().detect(ctx)

    assert result.status == DetectorStatus.RAN
    assert len(result.findings) == 1
    # ceiling 20%; excess = (40-20)% of 1000*1 = 200
    assert result.findings[0].financial_impact.amount == Decimal("200")


def test_flags_discount_above_ceiling_by_amount(ctx_factory):
    orders = [
        {"customer_id": "C1", "product_id": "P1", "list_price": "1000", "quantity": "1", "discount_amount": "500", "currency": "INR"},
    ]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders))
    result = DiscountLeakDetector().detect(ctx)
    # implied pct = 500/1000 = 50% > 20% ceiling; ceiling amount = 200; excess = 500-200=300
    assert result.findings[0].financial_impact.amount == Decimal("300")


def test_no_finding_within_policy(ctx_factory):
    orders = [{"customer_id": "C1", "product_id": "P1", "unit_price": "1000", "quantity": "1", "discount_percent": "10"}]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders))
    result = DiscountLeakDetector().detect(ctx)
    assert result.findings == []


def test_skips_without_discount_fields(ctx_factory):
    orders = [{"customer_id": "C1", "product_id": "P1", "unit_price": "1000", "quantity": "1"}]
    ctx = ctx_factory(("orders.csv", DatasetKind.ORDERS, orders))
    result = DiscountLeakDetector().detect(ctx)
    assert result.status == DetectorStatus.SKIPPED_MISSING_FIELDS
