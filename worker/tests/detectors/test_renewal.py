from datetime import date, timedelta
from decimal import Decimal

from app.detectors.renewal import RenewalLeakDetector
from app.schemas.domain import DatasetKind, DetectorStatus, ImpactType


def test_flags_contracts_expiring_within_30_days(ctx_factory):
    today = date(2026, 1, 1)
    contracts = [
        {"contract_id": "K1", "customer_id": "C1", "total_amount": "48000", "currency": "INR",
         "contract_end_date": (today + timedelta(days=10)).isoformat()},
        {"contract_id": "K2", "customer_id": "C2", "total_amount": "12000", "currency": "INR",
         "contract_end_date": (today + timedelta(days=90)).isoformat()},  # outside window
    ]
    ctx = ctx_factory(("contracts.csv", DatasetKind.CONTRACTS, contracts))
    result = RenewalLeakDetector(today=today).detect(ctx)

    assert result.status == DetectorStatus.RAN
    expiring = [f for f in result.findings if "expiring" in f.title.lower()]
    assert len(expiring) == 1
    assert expiring[0].financial_impact.amount == Decimal("48000")
    assert expiring[0].financial_impact.impact_type == ImpactType.AT_RISK_REVENUE
    assert expiring[0].financial_impact.is_recurring is True


def test_flags_already_expired_contracts_separately(ctx_factory):
    today = date(2026, 1, 1)
    contracts = [
        {"contract_id": "K1", "total_amount": "20000", "contract_end_date": (today - timedelta(days=5)).isoformat()},
    ]
    ctx = ctx_factory(("contracts.csv", DatasetKind.CONTRACTS, contracts))
    result = RenewalLeakDetector(today=today).detect(ctx)

    expired = [f for f in result.findings if "past" in f.title.lower()]
    assert len(expired) == 1
    assert expired[0].financial_impact.amount == Decimal("20000")


def test_skips_without_contracts_dataset(ctx_factory):
    ctx = ctx_factory()
    result = RenewalLeakDetector().detect(ctx)
    assert result.status == DetectorStatus.SKIPPED_MISSING_FIELDS


def test_never_reports_potential_leakage_impact_type(ctx_factory):
    today = date(2026, 1, 1)
    contracts = [{"contract_id": "K1", "total_amount": "1000", "contract_end_date": today.isoformat()}]
    ctx = ctx_factory(("contracts.csv", DatasetKind.CONTRACTS, contracts))
    result = RenewalLeakDetector(today=today).detect(ctx)
    for f in result.findings:
        assert f.financial_impact.impact_type == ImpactType.AT_RISK_REVENUE
