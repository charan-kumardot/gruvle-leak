from __future__ import annotations

import pytest

from app.detectors.base import DatasetBundle, DetectionContext
from app.schemas.domain import DatasetKind, NormalizedRecord


def make_records(dataset_id: str, rows: list[dict]) -> list[NormalizedRecord]:
    return [NormalizedRecord(dataset_id=dataset_id, row_index=i, values=row) for i, row in enumerate(rows)]


def make_ctx(*bundles_spec: tuple[str, DatasetKind, list[dict]], currency: str = "INR") -> DetectionContext:
    bundles = [
        DatasetBundle(dataset_id=ds_id, kind=kind, records=make_records(ds_id, rows))
        for ds_id, kind, rows in bundles_spec
    ]
    return DetectionContext(scan_id="scan-1", business_id="biz-1", default_currency=currency, datasets=bundles)


@pytest.fixture
def ctx_factory():
    return make_ctx
