"""
Declarative Appwrite database schema for Gruvle Leak.

This is the single source of truth for collections/attributes/indexes.
`scripts/provision_appwrite.py` reads this module and applies it idempotently
(create-if-missing) against the target Appwrite project — see spec section 49
(schema mirrors: users, businesses, datasets, dataset_files, dataset_columns,
data_mappings, scans, scan_jobs, leak_findings, leak_evidence,
leak_calculations, recommended_actions, reports, audit_logs, usage_events).

Multi-tenancy (spec section 57): Appwrite has no SQL row-level security, so
isolation is enforced with Appwrite Teams — one Team per business. Every
document in every business-owned collection is created with permissions
scoped to `team:<businessId>` (read/write), never to `any` or `users`. This
is enforced in code (see app/db/repositories.py) and verified by the IDOR
test suite (tests/test_multi_tenancy.py, added in the API delivery pass).

Note on `team_id`: every business-scoped collection below carries both
`business_id` (the owning `businesses` document's ID — the stable foreign
key other records join on) and `team_id` (the Appwrite Team ID backing that
business — the value Appwrite permissions and repository-layer isolation
checks actually key off of). Denormalizing `team_id` onto every document
lets `app/db/repositories.py` verify tenant ownership with a single document
read instead of a `businesses` lookup on every access, which matters because
the worker service talks to Appwrite with a privileged API key that (unlike
an end-user session) is not itself constrained by document permissions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from appwrite.permission import Permission
from appwrite.role import Role


class AttrType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    ENUM = "enum"


@dataclass
class Attribute:
    key: str
    type: AttrType
    size: int | None = None          # required for STRING
    required: bool = False
    default: object = None
    array: bool = False
    elements: list[str] | None = None  # required for ENUM


@dataclass
class Index:
    key: str
    type: str  # "key" | "unique" | "fulltext"
    attributes: list[str]


@dataclass
class CollectionDef:
    id: str
    name: str
    attributes: list[Attribute] = field(default_factory=list)
    indexes: list[Index] = field(default_factory=list)
    document_security: bool = True  # per-document permissions (business isolation)
    # Collection-level permissions — these govern `create` specifically:
    # Appwrite's document-level permissions (`document_security`) only ever
    # apply to a document that already exists (read/update/delete on THAT
    # document); creating a NEW document is authorized solely by the
    # collection's own permission list. Every collection here defaults to
    # `[]` (nobody but the worker's privileged API key can create in it) —
    # `businesses` is the sole exception: it's the one collection an
    # end user's own client-side session creates a document in directly,
    # during onboarding (see web/src/app/(app)/onboarding/page.tsx), so it
    # grants `create` to any authenticated user. Every other collection
    # (datasets, scans, leak_findings, ...) is written only by the worker
    # service via its server API key, which isn't constrained by
    # permissions at all — those stay at `[]` deliberately, since granting
    # `create` there would let a client-side session forge documents (e.g.
    # a fake completed scan or finding) the worker never actually computed.
    permissions: list[str] = field(default_factory=list)


DATABASE_ID = "gruvle_leak"

# Attribute + index added to every business-scoped collection (all except
# `businesses` itself, which already has its own `team_id`). See module
# docstring for why `team_id` is denormalized here rather than looked up.
# Factory functions (not shared instances) since Attribute/Index are mutable
# dataclasses and each collection below needs its own object.
def _team_attr() -> Attribute:
    return Attribute("team_id", AttrType.STRING, size=64, required=True)


def _team_index() -> Index:
    return Index("idx_team", "key", ["team_id"])

COLLECTIONS: list[CollectionDef] = [
    CollectionDef(
        id="businesses",
        name="Businesses",
        # Any authenticated user may CREATE a businesses document (they do,
        # during onboarding) — read/update/delete on that specific document
        # stays scoped to its team via document-level permissions, applied
        # at creation time by onboarding itself (see the docstring above).
        permissions=[Permission.create(Role.users())],
        attributes=[
            Attribute("owner_user_id", AttrType.STRING, size=64, required=True),
            Attribute("team_id", AttrType.STRING, size=64, required=True),
            Attribute("name", AttrType.STRING, size=256, required=True),
            Attribute("industry", AttrType.STRING, size=128),
            Attribute("currency", AttrType.STRING, size=8, default="INR"),
            Attribute("business_model", AttrType.STRING, size=128),
            Attribute("avg_order_value", AttrType.FLOAT),
            Attribute("billing_frequency", AttrType.STRING, size=32),
            Attribute("fiscal_year_start_month", AttrType.INTEGER, default=1),
            Attribute("plan", AttrType.ENUM, elements=["free", "starter", "growth", "business"], default="free"),
            Attribute("is_deleted", AttrType.BOOLEAN, default=False),
        ],
        indexes=[
            Index("idx_owner", "key", ["owner_user_id"]),
            Index("idx_team", "key", ["team_id"]),
        ],
    ),
    CollectionDef(
        id="datasets",
        name="Datasets",
        attributes=[
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("scan_id", AttrType.STRING, size=64),
            Attribute("kind", AttrType.STRING, size=32, required=True),
            Attribute("original_filename", AttrType.STRING, size=512, required=True),
            Attribute("file_type", AttrType.STRING, size=16, required=True),
            Attribute("file_size_bytes", AttrType.INTEGER, required=True),
            Attribute("storage_file_id", AttrType.STRING, size=128, required=True),
            Attribute("row_count", AttrType.INTEGER, default=0),
            Attribute("column_count", AttrType.INTEGER, default=0),
            Attribute("processing_status", AttrType.ENUM,
                      elements=["pending", "processing", "profiled", "failed"], default="pending"),
            Attribute("error_message", AttrType.STRING, size=1024),
            Attribute("is_deleted", AttrType.BOOLEAN, default=False),
        ],
        indexes=[
            Index("idx_business", "key", ["business_id"]),
            Index("idx_scan", "key", ["scan_id"]),
            _team_index(),
        ],
    ),
    CollectionDef(
        id="dataset_columns",
        name="Dataset Columns",
        attributes=[
            Attribute("dataset_id", AttrType.STRING, size=64, required=True),
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("raw_name", AttrType.STRING, size=256, required=True),
            Attribute("inferred_type", AttrType.STRING, size=32, required=True),
            Attribute("non_null_count", AttrType.INTEGER, default=0),
            Attribute("null_count", AttrType.INTEGER, default=0),
            Attribute("distinct_count", AttrType.INTEGER, default=0),
        ],
        indexes=[Index("idx_dataset", "key", ["dataset_id"]), _team_index()],
    ),
    CollectionDef(
        id="data_mappings",
        name="Data Mappings",
        attributes=[
            Attribute("dataset_id", AttrType.STRING, size=64, required=True),
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("raw_name", AttrType.STRING, size=256, required=True),
            Attribute("canonical_field", AttrType.STRING, size=64),
            Attribute("confidence", AttrType.FLOAT, default=0),
            Attribute("source", AttrType.ENUM, elements=["heuristic", "ai", "user"], required=True),
            Attribute("reason", AttrType.STRING, size=512),
            Attribute("confirmed_by_user", AttrType.BOOLEAN, default=False),
        ],
        indexes=[Index("idx_dataset", "key", ["dataset_id"]), _team_index()],
    ),
    CollectionDef(
        id="scans",
        name="Scans",
        attributes=[
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("created_by_user_id", AttrType.STRING, size=64, required=True),
            Attribute("stage", AttrType.ENUM, elements=[
                "UPLOADING", "PROFILING", "MAPPING", "DETECTING", "SCORING",
                "GENERATING_REPORT", "COMPLETED", "FAILED",
            ], default="UPLOADING"),
            Attribute("progress_percent", AttrType.INTEGER, default=0),
            Attribute("progress_detail", AttrType.STRING, size=512),
            Attribute("records_analyzed", AttrType.INTEGER, default=0),
            Attribute("detectors_run", AttrType.STRING, size=2048, array=True),
            Attribute("data_quality_score", AttrType.INTEGER),
            Attribute("total_potential_leakage", AttrType.FLOAT, default=0),
            Attribute("total_high_confidence_leakage", AttrType.FLOAT, default=0),
            Attribute("finding_count", AttrType.INTEGER, default=0),
            Attribute("currency", AttrType.STRING, size=8, default="INR"),
            Attribute("error_message", AttrType.STRING, size=1024),
            Attribute("is_demo", AttrType.BOOLEAN, default=False),
            Attribute("is_deleted", AttrType.BOOLEAN, default=False),
        ],
        indexes=[
            Index("idx_business", "key", ["business_id"]),
            Index("idx_stage", "key", ["stage"]),
            _team_index(),
        ],
    ),
    CollectionDef(
        id="leak_findings",
        name="Leak Findings",
        attributes=[
            Attribute("scan_id", AttrType.STRING, size=64, required=True),
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("category", AttrType.STRING, size=32, required=True),
            Attribute("title", AttrType.STRING, size=256, required=True),
            Attribute("summary", AttrType.STRING, size=1024, required=True),
            Attribute("why_it_matters", AttrType.STRING, size=2048),
            Attribute("what_we_dont_know", AttrType.STRING, size=512, array=True),
            Attribute("recommended_action", AttrType.STRING, size=1024),
            Attribute("impact_type", AttrType.STRING, size=32, required=True),
            Attribute("impact_amount", AttrType.FLOAT, required=True),
            Attribute("currency", AttrType.STRING, size=8, required=True),
            Attribute("is_recurring", AttrType.BOOLEAN, default=False),
            Attribute("recurrence_period", AttrType.STRING, size=16),
            Attribute("confidence", AttrType.ENUM, elements=["HIGH", "MEDIUM", "LOW"], required=True),
            Attribute("confidence_explanation", AttrType.STRING, size=1024),
            Attribute("urgency", AttrType.FLOAT, default=0),
            Attribute("recoverability", AttrType.FLOAT, default=0),
            Attribute("priority_score", AttrType.FLOAT, default=0),
            Attribute("detection_method", AttrType.STRING, size=256),
            Attribute("source_dataset_ids", AttrType.STRING, size=64, array=True),
            Attribute("status", AttrType.ENUM,
                      elements=["NEW", "REVIEWING", "CONFIRMED", "DISMISSED", "RESOLVED"], default="NEW"),
            Attribute("dismissal_reason", AttrType.STRING, size=512),
            Attribute("resolution_notes", AttrType.STRING, size=1024),
            Attribute("resolved_amount", AttrType.FLOAT),
            Attribute("resolved_at", AttrType.DATETIME),
            Attribute("owner_user_id", AttrType.STRING, size=64),
            Attribute("is_demo", AttrType.BOOLEAN, default=False),
        ],
        indexes=[
            Index("idx_scan", "key", ["scan_id"]),
            Index("idx_business", "key", ["business_id"]),
            Index("idx_category", "key", ["category"]),
            Index("idx_status", "key", ["status"]),
            _team_index(),
        ],
    ),
    CollectionDef(
        id="leak_evidence",
        name="Leak Evidence",
        attributes=[
            Attribute("finding_id", AttrType.STRING, size=64, required=True),
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("dataset_id", AttrType.STRING, size=64, required=True),
            Attribute("row_index", AttrType.INTEGER, required=True),
            Attribute("display_fields_json", AttrType.STRING, size=4096, required=True),
        ],
        indexes=[Index("idx_finding", "key", ["finding_id"]), _team_index()],
    ),
    CollectionDef(
        id="leak_calculations",
        name="Leak Calculations",
        attributes=[
            Attribute("finding_id", AttrType.STRING, size=64, required=True),
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("method", AttrType.STRING, size=256, required=True),
            Attribute("formula", AttrType.STRING, size=1024, required=True),
            Attribute("inputs_json", AttrType.STRING, size=4096),
            Attribute("result", AttrType.FLOAT, required=True),
        ],
        indexes=[Index("idx_finding", "key", ["finding_id"]), _team_index()],
    ),
    CollectionDef(
        id="recommended_actions",
        name="Recommended Actions",
        attributes=[
            Attribute("finding_id", AttrType.STRING, size=64, required=True),
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("action_type", AttrType.STRING, size=64, required=True),
            Attribute("title", AttrType.STRING, size=256, required=True),
            Attribute("draft_content", AttrType.STRING, size=4096),
            Attribute("potential_impact", AttrType.FLOAT),
            Attribute("status", AttrType.ENUM,
                      elements=["draft", "awaiting_approval", "approved", "completed", "dismissed"],
                      default="draft"),
            Attribute("owner_user_id", AttrType.STRING, size=64),
            Attribute("idempotency_key", AttrType.STRING, size=128),
        ],
        indexes=[
            Index("idx_finding", "key", ["finding_id"]),
            Index("idx_business", "key", ["business_id"]),
            Index("idx_idempotency", "unique", ["idempotency_key"]),
            _team_index(),
        ],
    ),
    CollectionDef(
        id="reports",
        name="Reports",
        attributes=[
            Attribute("scan_id", AttrType.STRING, size=64, required=True),
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("format", AttrType.ENUM, elements=["pdf", "csv", "json", "markdown"], required=True),
            Attribute("storage_file_id", AttrType.STRING, size=128),
            Attribute("summary_json", AttrType.STRING, size=8192),
            Attribute("is_deleted", AttrType.BOOLEAN, default=False),
        ],
        indexes=[Index("idx_scan", "key", ["scan_id"]), _team_index()],
    ),
    CollectionDef(
        id="audit_logs",
        name="Audit Logs",
        attributes=[
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("user_id", AttrType.STRING, size=64, required=True),
            Attribute("action", AttrType.STRING, size=128, required=True),
            Attribute("object_type", AttrType.STRING, size=64, required=True),
            Attribute("object_id", AttrType.STRING, size=64, required=True),
            Attribute("before_state_json", AttrType.STRING, size=4096),
            Attribute("after_state_json", AttrType.STRING, size=4096),
            Attribute("ip_address", AttrType.STRING, size=64),
        ],
        indexes=[
            Index("idx_business", "key", ["business_id"]),
            Index("idx_object", "key", ["object_type", "object_id"]),
            _team_index(),
        ],
    ),
    CollectionDef(
        id="usage_events",
        name="Usage Events",
        attributes=[
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("user_id", AttrType.STRING, size=64),
            Attribute("event_name", AttrType.STRING, size=128, required=True),
            Attribute("metadata_json", AttrType.STRING, size=2048),
        ],
        indexes=[
            Index("idx_business", "key", ["business_id"]),
            Index("idx_event", "key", ["event_name"]),
            _team_index(),
        ],
    ),
    CollectionDef(
        id="finding_feedback",
        name="Finding Feedback",
        attributes=[
            Attribute("finding_id", AttrType.STRING, size=64, required=True),
            Attribute("business_id", AttrType.STRING, size=64, required=True),
            _team_attr(),
            Attribute("user_id", AttrType.STRING, size=64, required=True),
            Attribute("verdict", AttrType.ENUM, elements=["confirmed", "false_positive", "resolved"], required=True),
            Attribute("reason", AttrType.STRING, size=1024),
        ],
        indexes=[Index("idx_finding", "key", ["finding_id"]), _team_index()],
    ),
]

STORAGE_BUCKETS = [
    # A single shared bucket, not the two originally intended ("raw_uploads" +
    # "generated_reports"). Two hard platform/plan limits, both discovered
    # live while provisioning, forced this:
    #   1. `maximumFileSize` is capped at 50,000,000 bytes on this Appwrite
    #      Cloud plan ("Value must be a valid range between 1 and
    #      50,000,000") — 45MB keeps a safety margin under that ceiling.
    #   2. The plan also caps the project to a SINGLE storage bucket
    #      ("The maximum number of buckets allowed for the selected plan has
    #      been reached") — a second `create_bucket` call fails outright, no
    #      API key scope fixes it.
    # Original uploads and generated reports are both stored here, kept
    # apart only by a filename convention the storage layer applies
    # (`upload/<dataset_id>/<filename>` vs `report/<scan_id>/<format>`) —
    # both are already private, per-document-permissioned files either way,
    # so one bucket vs. two changes naming, not security. The `id` stays
    # "generated_reports" because that bucket already exists live and this
    # plan has no quota left to create a differently-named replacement.
    {"id": "generated_reports", "name": "Gruvle Files", "max_file_size_mb": 45, "file_security": True},
]
