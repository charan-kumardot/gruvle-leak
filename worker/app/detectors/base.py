"""
LeakDetector interface (spec section 17) and the detection context every
detector runs against.

Hard rule enforced by this module's design: a detector receives already
*normalized* records (canonical field names, coerced types — see
app/mapping/normalize.py) and does its own arithmetic in plain Python using
`Decimal`. No detector may call an AI provider to compute a number. AI is
only ever used later, to phrase an explanation around a number a detector
already produced (see app/ai/router.py, called from the report layer, not
from here).
"""
from __future__ import annotations

import abc
from collections import defaultdict

from app.schemas.domain import DatasetKind, DetectorRunResult, LeakCategory, NormalizedRecord


class DatasetBundle:
    def __init__(self, dataset_id: str, kind: DatasetKind, records: list[NormalizedRecord]):
        self.dataset_id = dataset_id
        self.kind = kind
        self.records = records

    def values(self) -> list[dict]:
        """Convenience: the raw canonical-field dicts, in order."""
        return [r.values for r in self.records]


class DetectionContext:
    def __init__(self, scan_id: str, business_id: str, default_currency: str, datasets: list[DatasetBundle]):
        self.scan_id = scan_id
        self.business_id = business_id
        self.default_currency = default_currency
        self.datasets = datasets
        self._by_kind: dict[DatasetKind, list[DatasetBundle]] = defaultdict(list)
        for d in datasets:
            self._by_kind[d.kind].append(d)

    def bundles_of_kind(self, kind: DatasetKind) -> list[DatasetBundle]:
        return self._by_kind.get(kind, [])

    def records_of_kind(self, kind: DatasetKind) -> list[tuple[str, NormalizedRecord]]:
        """(dataset_id, record) pairs across all datasets of a given kind."""
        out = []
        for bundle in self.bundles_of_kind(kind):
            for r in bundle.records:
                out.append((bundle.dataset_id, r))
        return out

    def has_kind(self, kind: DatasetKind) -> bool:
        return kind in self._by_kind


class LeakDetector(abc.ABC):
    name: str
    category: LeakCategory

    @abc.abstractmethod
    def detect(self, ctx: DetectionContext) -> DetectorRunResult:
        ...

    def _skip(self, ctx: DetectionContext, reason: str, missing: bool = True) -> DetectorRunResult:
        from app.schemas.domain import DetectorStatus
        return DetectorRunResult(
            detector_name=self.name,
            category=self.category,
            status=DetectorStatus.SKIPPED_MISSING_FIELDS if missing else DetectorStatus.SKIPPED_NOT_IMPLEMENTED,
            skip_reason=reason,
        )
