"""
Core domain contracts for Gruvle Leak's detection engine.

These are the shapes every detector, the profiler, the mapper, and the API
agree on. Nothing here is provider-specific (no Appwrite, no Gemini) — this
module has zero I/O and zero external dependencies, so it can be unit tested
in isolation and reused unchanged if the storage/AI backend ever changes.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

class LeakCategory(str, Enum):
    UNBILLED = "UNBILLED"
    PRICING = "PRICING"
    INVOICE = "INVOICE"
    RENEWAL = "RENEWAL"
    INVENTORY = "INVENTORY"
    DISCOUNT = "DISCOUNT"
    REFUND = "REFUND"
    CUSTOMER = "CUSTOMER"
    CONTRACT = "CONTRACT"
    OPERATIONS = "OPERATIONS"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ImpactType(str, Enum):
    """
    Distinguishes fundamentally different kinds of financial claim.
    These must never be summed together into one misleading number
    (spec section 34) — a report totals them separately, by type.
    """
    POTENTIAL_LEAKAGE = "POTENTIAL_LEAKAGE"          # e.g. unbilled work, invoice mismatch
    AT_RISK_REVENUE = "AT_RISK_REVENUE"              # e.g. renewal / customer churn risk
    REVENUE_OPPORTUNITY = "REVENUE_OPPORTUNITY"      # e.g. underpricing vs. market
    CAPITAL_TIED_UP = "CAPITAL_TIED_UP"              # e.g. dead inventory


class FindingStatus(str, Enum):
    NEW = "NEW"
    REVIEWING = "REVIEWING"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class DetectorStatus(str, Enum):
    """Whether a detector actually ran, and if not, why."""
    RAN = "RAN"
    SKIPPED_MISSING_FIELDS = "SKIPPED_MISSING_FIELDS"
    SKIPPED_NOT_IMPLEMENTED = "SKIPPED_NOT_IMPLEMENTED"
    FAILED = "FAILED"


class CanonicalField(str, Enum):
    """
    The normalized column vocabulary every dataset gets mapped onto.
    Detectors are written against these names, never against raw
    spreadsheet headers.
    """
    CUSTOMER_ID = "customer_id"
    CUSTOMER_NAME = "customer_name"
    ORDER_ID = "order_id"
    INVOICE_ID = "invoice_id"
    CONTRACT_ID = "contract_id"
    PRODUCT_ID = "product_id"
    PRODUCT_NAME = "product_name"
    QUANTITY = "quantity"
    UNIT_PRICE = "unit_price"
    LIST_PRICE = "list_price"
    DISCOUNT_AMOUNT = "discount_amount"
    DISCOUNT_PERCENT = "discount_percent"
    TOTAL_AMOUNT = "total_amount"
    COST_AMOUNT = "cost_amount"
    TAX_AMOUNT = "tax_amount"
    CURRENCY = "currency"
    ORDER_DATE = "order_date"
    INVOICE_DATE = "invoice_date"
    DUE_DATE = "due_date"
    PAID_DATE = "paid_date"
    STATUS = "status"
    RENEWAL_DATE = "renewal_date"
    CONTRACT_START_DATE = "contract_start_date"
    CONTRACT_END_DATE = "contract_end_date"
    REFUND_AMOUNT = "refund_amount"
    REFUND_DATE = "refund_date"
    INVENTORY_QUANTITY = "inventory_quantity"
    LAST_MOVEMENT_DATE = "last_movement_date"
    PAYMENT_AMOUNT = "payment_amount"
    PAYMENT_DATE = "payment_date"


# ---------------------------------------------------------------------------
# Dataset / profiling
# ---------------------------------------------------------------------------

class DatasetKind(str, Enum):
    ORDERS = "ORDERS"
    INVOICES = "INVOICES"
    PAYMENTS = "PAYMENTS"
    CONTRACTS = "CONTRACTS"
    INVENTORY = "INVENTORY"
    CUSTOMERS = "CUSTOMERS"
    REFUNDS = "REFUNDS"
    UNKNOWN = "UNKNOWN"


class ColumnProfile(BaseModel):
    raw_name: str
    inferred_type: Literal["string", "integer", "float", "date", "boolean", "currency", "id"]
    non_null_count: int
    null_count: int
    distinct_count: int
    sample_values: list[Any] = Field(default_factory=list)
    looks_like_currency: bool = False
    looks_like_date: bool = False
    looks_like_id: bool = False


class DatasetProfile(BaseModel):
    dataset_id: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    duplicate_row_count: int
    inferred_kind: DatasetKind
    inferred_kind_confidence: float  # 0..1
    warnings: list[str] = Field(default_factory=list)


class ColumnMapping(BaseModel):
    raw_name: str
    canonical_field: Optional[CanonicalField]
    confidence: float  # 0..1
    source: Literal["heuristic", "ai", "user"]
    reason: str


class DataMapping(BaseModel):
    dataset_id: str
    mappings: list[ColumnMapping]
    unmapped_required_fields: list[CanonicalField] = Field(default_factory=list)


class DataQualityScore(BaseModel):
    overall_score: int  # 0-100
    completeness: int
    consistency: int
    duplicates: int
    required_fields: int
    date_coverage: int
    explanations: list[str] = Field(default_factory=list)
    affected_detectors: list[LeakCategory] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Normalized row (post-mapping, pre-detection)
# ---------------------------------------------------------------------------

class NormalizedRecord(BaseModel):
    """One row after column mapping, keyed by canonical field name."""
    dataset_id: str
    row_index: int
    values: dict[str, Any]


# ---------------------------------------------------------------------------
# Findings / evidence
# ---------------------------------------------------------------------------

class EvidenceRecordRef(BaseModel):
    dataset_id: str
    row_index: int
    display_fields: dict[str, Any]


class Calculation(BaseModel):
    """A fully transparent, reproducible arithmetic trail."""
    method: str                      # human-readable, e.g. "sum(completed_unbilled_orders)"
    formula: str                     # e.g. "25000 (order) - 0 (invoiced) = 25000"
    inputs: dict[str, Any] = Field(default_factory=dict)
    result: Decimal


class FinancialImpact(BaseModel):
    impact_type: ImpactType
    amount: Decimal
    currency: str
    is_recurring: bool = False
    recurrence_period: Optional[Literal["monthly", "quarterly", "yearly"]] = None


class LeakFinding(BaseModel):
    id: str
    scan_id: str
    business_id: str
    category: LeakCategory
    title: str
    summary: str                                   # one-line, evidence-hedged language
    why_it_matters: str
    what_we_dont_know: list[str] = Field(default_factory=list)
    recommended_action: str
    financial_impact: FinancialImpact
    confidence: Confidence
    confidence_explanation: str
    urgency: float                                  # 0..1, deterministic
    recoverability: float                            # 0..1, deterministic
    priority_score: float                            # normalized 0..100, computed — not AI-assigned
    evidence: list[EvidenceRecordRef]
    calculation: Calculation
    detection_method: str
    source_dataset_ids: list[str]
    status: FindingStatus = FindingStatus.NEW
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DetectorRunResult(BaseModel):
    detector_name: str
    category: LeakCategory
    status: DetectorStatus
    findings: list[LeakFinding] = Field(default_factory=list)
    skip_reason: Optional[str] = None
    records_evaluated: int = 0
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

class ScanStage(str, Enum):
    UPLOADING = "UPLOADING"
    PROFILING = "PROFILING"
    MAPPING = "MAPPING"
    DETECTING = "DETECTING"
    SCORING = "SCORING"
    GENERATING_REPORT = "GENERATING_REPORT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ScanProgress(BaseModel):
    scan_id: str
    stage: ScanStage
    detail: str
    percent: int  # 0-100, derived from actual completed steps, never fabricated
