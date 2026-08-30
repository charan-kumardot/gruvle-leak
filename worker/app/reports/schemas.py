from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.domain import Confidence, LeakFinding


class ImpactTotal(BaseModel):
    impact_type: str
    currency: str
    amount: Decimal


class ReportSummary(BaseModel):
    scan_id: str
    business_id: str
    business_name: str
    scan_date: date
    records_analyzed: int
    detectors_run: list[str]
    detectors_skipped: list[str]
    data_quality_score: int | None
    impact_totals: list[ImpactTotal]
    finding_count: int
    high_confidence_count: int
    top_findings: list[LeakFinding]
    all_findings: list[LeakFinding]
    data_limitations: list[str]
    is_demo: bool = False


def confidence_rank(c: Confidence) -> int:
    return {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}[c]
