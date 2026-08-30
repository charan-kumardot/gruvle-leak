from __future__ import annotations

from app.detectors.base import DetectionContext, LeakDetector
from app.detectors.discount import DiscountLeakDetector
from app.detectors.invoice_mismatch import InvoiceMismatchDetector
from app.detectors.pricing import PricingLeakDetector
from app.detectors.renewal import RenewalLeakDetector
from app.detectors.stubs import (
    ContractLeakDetector,
    CustomerLeakDetector,
    InventoryLeakDetector,
    OperationsLeakDetector,
    RefundLeakDetector,
)
from app.detectors.unbilled import UnbilledRevenueDetector
from app.schemas.domain import DetectorRunResult

ALL_DETECTORS: list[LeakDetector] = [
    UnbilledRevenueDetector(),
    PricingLeakDetector(),
    InvoiceMismatchDetector(),
    DiscountLeakDetector(),
    RenewalLeakDetector(),
    InventoryLeakDetector(),
    RefundLeakDetector(),
    CustomerLeakDetector(),
    ContractLeakDetector(),
    OperationsLeakDetector(),
]


def run_all_detectors(ctx: DetectionContext, detectors: list[LeakDetector] | None = None) -> list[DetectorRunResult]:
    """
    Runs every detector independently. A single detector raising an
    exception must never take down the whole scan — it's caught and
    reported as a FAILED DetectorRunResult so the rest of the scan's
    findings are still delivered (spec: partial results over total failure).
    """
    from app.schemas.domain import DetectorStatus

    results = []
    for detector in detectors if detectors is not None else ALL_DETECTORS:
        try:
            results.append(detector.detect(ctx))
        except Exception as e:  # noqa: BLE001 - deliberate: isolate detector failures
            results.append(DetectorRunResult(
                detector_name=detector.name,
                category=detector.category,
                status=DetectorStatus.FAILED,
                errors=[f"{type(e).__name__}: {e}"],
            ))
    return results
