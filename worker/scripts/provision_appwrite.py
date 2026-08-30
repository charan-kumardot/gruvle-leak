"""
Idempotent Appwrite provisioning script for Gruvle Leak.

Run (from `worker/`, with the venv active):

    source .venv/Scripts/activate
    python scripts/provision_appwrite.py

Reads `app/db/schema.py` (`COLLECTIONS`, `STORAGE_BUCKETS`) as the single
source of truth and creates whatever is missing on the live Appwrite project
referenced by `.env` — the database, each collection, each attribute, each
index, and each storage bucket. Every step first checks whether the resource
already exists, so re-running this script after a partial failure (or just
to pick up schema.py changes) is safe: existing resources are left alone and
reported as "exists" rather than being recreated or erroring out.

Collections are created with `document_security=True` and NO collection-level
permissions (`permissions=[]`) — nobody gets access to a document just by
virtue of being logged in or being any user at all. Access is granted only
per-document, at write time, scoped to the owning business's Appwrite Team
(see `app/db/repositories.py`). Storage buckets are created the same way:
`file_security=True`, no bucket-level permissions, so uploaded business data
is never publicly or cross-tenant readable.

Failure handling: each resource (collection, attribute, index, bucket) is
attempted independently. A failure on one is logged and does not stop the
script from attempting the rest, so a partial re-run can make forward
progress. The script exits non-zero iff anything failed.
"""
from __future__ import annotations

import sys
import time
import warnings

from appwrite.exception import AppwriteException

# The installed appwrite==23.0.0 SDK still exposes the Databases-service
# collection/attribute/index/document APIs used throughout this script (and
# app/db/client.py), but as of Appwrite 1.8 marks them deprecated in favor of
# a newer `TablesDB` service. We deliberately keep using Databases for now
# for consistency with the rest of this codebase; silence the resulting
# per-call DeprecationWarning noise so real failures aren't buried under it.
warnings.filterwarnings("ignore", category=DeprecationWarning, module="appwrite")

from app.core.config import get_settings
from app.db.client import get_databases, get_storage
from app.db.schema import COLLECTIONS, DATABASE_ID, STORAGE_BUCKETS, Attribute, AttrType, CollectionDef, Index

HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409

ATTRIBUTE_WAIT_TIMEOUT_S = 90
ATTRIBUTE_POLL_INTERVAL_S = 1.5


class Report:
    """Accumulates a human-readable created/exists/failed log as we go."""

    def __init__(self) -> None:
        self.created: list[str] = []
        self.exists: list[str] = []
        self.failed: list[str] = []

    def ok(self, label: str) -> None:
        self.created.append(label)
        print(f"  [created]  {label}")

    def skip(self, label: str) -> None:
        self.exists.append(label)
        print(f"  [exists]   {label}")

    def fail(self, label: str, err: object) -> None:
        self.failed.append(label)
        print(f"  [FAILED]   {label}: {err}")


def _code(e: AppwriteException) -> int | None:
    return getattr(e, "code", None)


def is_not_found(e: AppwriteException) -> bool:
    return _code(e) == HTTP_NOT_FOUND


def is_conflict(e: AppwriteException) -> bool:
    return _code(e) == HTTP_CONFLICT


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def ensure_database(databases, report: Report) -> bool:
    label = f"database '{DATABASE_ID}'"
    try:
        databases.get(DATABASE_ID)
        report.skip(label)
        return True
    except AppwriteException as e:
        if not is_not_found(e):
            report.fail(f"{label} (get)", e.message)
            return False

    try:
        databases.create(database_id=DATABASE_ID, name="Gruvle Leak")
        report.ok(label)
        return True
    except AppwriteException as e:
        if is_conflict(e):
            report.skip(label)
            return True
        report.fail(f"{label} (create)", e.message)
        return False


# ---------------------------------------------------------------------------
# Attributes
# ---------------------------------------------------------------------------

def _create_attribute(databases, collection_id: str, attr: Attribute) -> None:
    # Appwrite rejects a `default` combined with required=True or array=True.
    default = None if (attr.required or attr.array) else attr.default

    if attr.type == AttrType.STRING:
        databases.create_string_attribute(
            database_id=DATABASE_ID, collection_id=collection_id, key=attr.key,
            size=attr.size or 255, required=attr.required, default=default, array=attr.array,
        )
    elif attr.type == AttrType.INTEGER:
        databases.create_integer_attribute(
            database_id=DATABASE_ID, collection_id=collection_id, key=attr.key,
            required=attr.required, default=default, array=attr.array,
        )
    elif attr.type == AttrType.FLOAT:
        databases.create_float_attribute(
            database_id=DATABASE_ID, collection_id=collection_id, key=attr.key,
            required=attr.required, default=default, array=attr.array,
        )
    elif attr.type == AttrType.BOOLEAN:
        databases.create_boolean_attribute(
            database_id=DATABASE_ID, collection_id=collection_id, key=attr.key,
            required=attr.required, default=default, array=attr.array,
        )
    elif attr.type == AttrType.DATETIME:
        databases.create_datetime_attribute(
            database_id=DATABASE_ID, collection_id=collection_id, key=attr.key,
            required=attr.required, default=default, array=attr.array,
        )
    elif attr.type == AttrType.ENUM:
        if not attr.elements:
            raise ValueError(f"enum attribute '{attr.key}' has no `elements` defined in schema.py")
        databases.create_enum_attribute(
            database_id=DATABASE_ID, collection_id=collection_id, key=attr.key,
            elements=attr.elements, required=attr.required, default=default, array=attr.array,
        )
    else:
        raise ValueError(f"unhandled AttrType: {attr.type}")


def _attribute_status(attr_obj) -> str | None:
    if isinstance(attr_obj, dict):
        raw = attr_obj.get("status")
    else:
        raw = getattr(attr_obj, "status", None)
    # The SDK models this as an `AttributeStatus` enum member, not a plain
    # str, even though `AttrType`/model fields elsewhere are str-enums —
    # unwrap `.value` so comparisons against plain strings work either way.
    return getattr(raw, "value", raw)


def wait_for_attribute(databases, collection_id: str, key: str, report: Report) -> bool:
    """Polls until the attribute is 'available' (Appwrite indexes async)."""
    deadline = time.monotonic() + ATTRIBUTE_WAIT_TIMEOUT_S
    while True:
        try:
            attr_obj = databases.get_attribute(DATABASE_ID, collection_id, key)
        except AppwriteException as e:
            report.fail(f"{collection_id}.{key} (waiting for availability)", e.message)
            return False

        status = _attribute_status(attr_obj)
        if status == "available":
            return True
        if status == "failed":
            report.fail(f"{collection_id}.{key}", "Appwrite reports attribute status 'failed'")
            return False
        if time.monotonic() >= deadline:
            report.fail(
                f"{collection_id}.{key}",
                f"did not become 'available' within {ATTRIBUTE_WAIT_TIMEOUT_S}s (last status: {status!r})",
            )
            return False
        time.sleep(ATTRIBUTE_POLL_INTERVAL_S)


def ensure_attribute(databases, collection_id: str, attr: Attribute, report: Report) -> bool:
    label = f"{collection_id}.{attr.key} (attribute)"
    try:
        databases.get_attribute(DATABASE_ID, collection_id, attr.key)
        report.skip(label)
        return True
    except AppwriteException as e:
        if not is_not_found(e):
            report.fail(label, e.message)
            return False

    try:
        _create_attribute(databases, collection_id, attr)
    except AppwriteException as e:
        if is_conflict(e):
            report.skip(label)
        else:
            report.fail(label, e.message)
            return False
    except ValueError as e:
        report.fail(label, str(e))
        return False

    if wait_for_attribute(databases, collection_id, attr.key, report):
        report.ok(label)
        return True
    return False


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

def ensure_index(databases, collection_id: str, index: Index, report: Report) -> bool:
    label = f"{collection_id}.{index.key} (index)"
    try:
        databases.get_index(DATABASE_ID, collection_id, index.key)
        report.skip(label)
        return True
    except AppwriteException as e:
        if not is_not_found(e):
            report.fail(label, e.message)
            return False

    try:
        databases.create_index(
            database_id=DATABASE_ID, collection_id=collection_id, key=index.key,
            type=index.type, attributes=index.attributes,
        )
        report.ok(label)
        return True
    except AppwriteException as e:
        if is_conflict(e):
            report.skip(label)
            return True
        report.fail(label, e.message)
        return False


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

def ensure_collection(databases, coll: CollectionDef, report: Report) -> None:
    label = f"collection '{coll.id}'"
    try:
        existing = databases.get_collection(DATABASE_ID, coll.id)
        existing_permissions = existing.get("$permissions") if isinstance(existing, dict) else getattr(existing, "permissions", None)
        if set(existing_permissions or []) != set(coll.permissions):
            try:
                databases.update_collection(
                    database_id=DATABASE_ID, collection_id=coll.id, name=coll.name,
                    permissions=coll.permissions, document_security=coll.document_security,
                )
                report.ok(f"{label} (updated collection-level permissions -> {coll.permissions})")
            except AppwriteException as e:
                report.fail(f"{label} (update permissions)", e.message)
        else:
            report.skip(label)
    except AppwriteException as e:
        if not is_not_found(e):
            report.fail(label, e.message)
            return
        try:
            databases.create_collection(
                database_id=DATABASE_ID, collection_id=coll.id, name=coll.name,
                permissions=coll.permissions,
                document_security=coll.document_security,
            )
            report.ok(label)
        except AppwriteException as e2:
            if is_conflict(e2):
                report.skip(label)
            else:
                report.fail(label, e2.message)
                return

    for attr in coll.attributes:
        ensure_attribute(databases, coll.id, attr, report)

    # Every attribute an index references must be available before the index
    # is created, so re-check (cheap: these should already be available from
    # the loop above, but a prior partial run may have left some pending).
    needed = {key for idx in coll.indexes for key in idx.attributes}
    all_ready = True
    for key in needed:
        if not wait_for_attribute(databases, coll.id, key, report):
            all_ready = False
    if not all_ready:
        report.fail(f"collection '{coll.id}' indexes",
                     "skipped all indexes — one or more required attributes never became available")
        return

    for index in coll.indexes:
        ensure_index(databases, coll.id, index, report)


# ---------------------------------------------------------------------------
# Storage buckets
# ---------------------------------------------------------------------------

def ensure_bucket(storage, bucket: dict, report: Report) -> None:
    label = f"bucket '{bucket['id']}'"
    target_size_bytes = bucket["max_file_size_mb"] * 1024 * 1024
    try:
        existing = storage.get_bucket(bucket["id"])
        # SDK model attribute is `maximumfilesize` (all lowercase, no
        # underscore) — confirmed by inspecting the live object; the raw
        # REST API's `maximumFileSize` only applies to the dict/JSON shape.
        current_size = existing.get("maximumFileSize") if isinstance(existing, dict) else getattr(existing, "maximumfilesize", None)
        if current_size is not None:
            current_size = int(current_size)
        if current_size != target_size_bytes:
            try:
                storage.update_bucket(
                    bucket_id=bucket["id"], name=bucket["name"],
                    file_security=bucket.get("file_security", True),
                    maximum_file_size=target_size_bytes,
                )
                report.ok(f"{label} (updated maximumFileSize {current_size} -> {target_size_bytes})")
            except AppwriteException as e:
                report.fail(f"{label} (update maximumFileSize)", e.message)
        else:
            report.skip(label)
        return
    except AppwriteException as e:
        if not is_not_found(e):
            report.fail(label, e.message)
            return

    try:
        storage.create_bucket(
            bucket_id=bucket["id"],
            name=bucket["name"],
            permissions=[],  # private by default — no public read, no any/users access
            file_security=bucket.get("file_security", True),
            maximum_file_size=bucket["max_file_size_mb"] * 1024 * 1024,
        )
        report.ok(label)
    except AppwriteException as e:
        if is_conflict(e):
            report.skip(label)
        else:
            report.fail(label, e.message)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    settings = get_settings()
    if not settings.appwrite_configured:
        print("APPWRITE_PROJECT_ID / APPWRITE_API_KEY are not set (see .env) — nothing to provision.")
        print(
            "The server API key needs these scopes: databases.read, databases.write, "
            "collections.read, collections.write, attributes.read, attributes.write, "
            "indexes.read, indexes.write, documents.read, documents.write, buckets.read, "
            "buckets.write, files.read, files.write, teams.read, teams.write."
        )
        return 1

    databases = get_databases()
    storage = get_storage()
    report = Report()

    print(f"Provisioning Appwrite project '{settings.appwrite_project_id}' at {settings.appwrite_endpoint}")

    print("\n== Database ==")
    db_ok = ensure_database(databases, report)

    if db_ok:
        for coll in COLLECTIONS:
            print(f"\n== Collection: {coll.id} ==")
            ensure_collection(databases, coll, report)
    else:
        print("\nDatabase is unavailable — skipping all collections.")
        for coll in COLLECTIONS:
            report.fail(f"collection '{coll.id}'", "skipped — database unavailable")

    print("\n== Storage buckets ==")
    for bucket in STORAGE_BUCKETS:
        ensure_bucket(storage, bucket, report)

    print("\n" + "=" * 70)
    print(f"Created: {len(report.created)}   Already existed: {len(report.exists)}   Failed: {len(report.failed)}")
    if report.failed:
        print("\nFailures:")
        for f in report.failed:
            print(f"  - {f}")
        print(
            "\nIf failures mention 401/403, the API key is missing one of the scopes "
            "listed above — add it in the Appwrite console (Project Settings -> API Keys) "
            "and re-run this script; it is safe to re-run."
        )
        return 1

    print("\nProvisioning complete — all resources present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
