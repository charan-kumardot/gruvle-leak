"""Small shared helpers used by every detector — kept tiny and dependency-free
so they're trivial to unit test and reason about (no hidden magic)."""
from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.domain import EvidenceRecordRef


def to_decimal(value: Any) -> Decimal | None:
    """Never go through float for money — str() first avoids binary rounding error."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def new_id() -> str:
    return str(uuid.uuid4())


def evidence_from(dataset_id: str, row_index: int, values: dict, fields: list[str]) -> EvidenceRecordRef:
    return EvidenceRecordRef(
        dataset_id=dataset_id,
        row_index=row_index,
        display_fields={f: values.get(f) for f in fields if f in values},
    )


COMPLETED_STATUSES = {
    "completed", "complete", "delivered", "fulfilled", "closed", "done", "shipped", "paid",
}

CANCELLED_STATUSES = {"cancelled", "canceled", "void", "voided", "refunded"}


def is_completed_status(status: Any) -> bool:
    if not isinstance(status, str):
        return False
    return status.strip().lower() in COMPLETED_STATUSES
