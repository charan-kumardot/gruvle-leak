"""
Registered-but-not-yet-implemented detectors (spec categories: INVENTORY,
REFUND, CUSTOMER, CONTRACT, OPERATIONS).

These exist so the full category list is visible in filters and the API
from day one, and so adding real logic later is additive (register real
findings) rather than a breaking change to the API/UI contract. They never
fabricate a finding — they always return SKIPPED_NOT_IMPLEMENTED with a
category-specific explanation of what data/logic would be needed.
"""
from __future__ import annotations

from app.detectors.base import DetectionContext, LeakDetector
from app.schemas.domain import DetectorRunResult, DetectorStatus, LeakCategory


class _NotImplementedDetector(LeakDetector):
    _reason: str

    def detect(self, ctx: DetectionContext) -> DetectorRunResult:
        return DetectorRunResult(
            detector_name=self.name,
            category=self.category,
            status=DetectorStatus.SKIPPED_NOT_IMPLEMENTED,
            skip_reason=self._reason,
        )


class InventoryLeakDetector(_NotImplementedDetector):
    name = "InventoryLeakDetector"
    category = LeakCategory.INVENTORY
    _reason = "Inventory leak detection is not yet implemented for this dataset shape."


class RefundLeakDetector(_NotImplementedDetector):
    name = "RefundLeakDetector"
    category = LeakCategory.REFUND
    _reason = "Refund anomaly detection is not yet implemented for this dataset shape."


class CustomerLeakDetector(_NotImplementedDetector):
    name = "CustomerLeakDetector"
    category = LeakCategory.CUSTOMER
    _reason = "Customer revenue-risk detection is not yet implemented for this dataset shape."


class ContractLeakDetector(_NotImplementedDetector):
    name = "ContractLeakDetector"
    category = LeakCategory.CONTRACT
    _reason = "Contract term extraction and comparison is not yet implemented for this dataset shape."


class OperationsLeakDetector(_NotImplementedDetector):
    name = "OperationsLeakDetector"
    category = LeakCategory.OPERATIONS
    _reason = "Operations-to-financial-impact detection is not yet implemented for this dataset shape."
