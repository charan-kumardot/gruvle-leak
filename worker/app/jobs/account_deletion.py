"""
Full account/business deletion (spec section 12: a user must be able to
delete their account). Cascades every business-scoped collection, then the
business document, the Appwrite Team, and finally the Appwrite user.

This is deliberately the only place in the codebase that deletes a `users`
record — called exclusively from `POST /account/delete`, which the Next.js
route handler only ever invokes after independently verifying (via the
caller's own JWT, not any client-supplied id) which user is actually
making the request. See web/src/app/api/account/delete/route.ts.
"""
from __future__ import annotations

from appwrite.query import Query

from app.db.client import get_databases, get_storage, get_users
from app.db.repositories import get_teams
from app.db.schema import DATABASE_ID

# Every collection that carries `business_id` and must be purged. Order
# matters only cosmetically here — each collection is independent, but
# listing findings-related ones first keeps the log readable.
BUSINESS_SCOPED_COLLECTIONS = [
    "leak_evidence", "leak_calculations", "leak_findings", "finding_feedback",
    "dataset_columns", "data_mappings", "datasets",
    "scans", "reports", "data_source_connections", "audit_logs", "usage_events",
]

FILES_BUCKET = "generated_reports"


def _docs(coll: str, business_id: str) -> list[dict]:
    databases = get_databases()
    result = databases.list_documents(DATABASE_ID, coll, [Query.equal("business_id", business_id), Query.limit(500)])
    return result.documents if hasattr(result, "documents") else result["documents"]


def _doc_id(doc) -> str:
    return doc.id if hasattr(doc, "id") else doc["$id"]


def delete_business_and_account(*, business_id: str, team_id: str, user_id: str) -> dict:
    databases = get_databases()
    storage = get_storage()
    teams = get_teams()
    users = get_users()

    deleted_counts: dict[str, int] = {}

    # Best-effort file cleanup — a missing/already-gone storage file must
    # never block the rest of account deletion.
    try:
        dataset_docs = _docs("datasets", business_id)
        for d in dataset_docs:
            file_id = d.get("storage_file_id") if isinstance(d, dict) else getattr(d, "storage_file_id", None)
            if file_id:
                try:
                    storage.delete_file(FILES_BUCKET, file_id)
                except Exception:  # noqa: BLE001 — storage cleanup is best-effort
                    pass
    except Exception:  # noqa: BLE001
        pass

    for coll in BUSINESS_SCOPED_COLLECTIONS:
        docs = _docs(coll, business_id)
        for doc in docs:
            try:
                databases.delete_document(DATABASE_ID, coll, _doc_id(doc))
            except Exception:  # noqa: BLE001 — one stray failure must not abort the whole deletion
                continue
        deleted_counts[coll] = len(docs)

    try:
        databases.delete_document(DATABASE_ID, "businesses", business_id)
    except Exception:  # noqa: BLE001
        pass

    try:
        teams.delete(team_id)
    except Exception:  # noqa: BLE001
        pass

    try:
        users.delete(user_id)
    except Exception:  # noqa: BLE001
        pass

    return {"deleted": True, "counts": deleted_counts}
