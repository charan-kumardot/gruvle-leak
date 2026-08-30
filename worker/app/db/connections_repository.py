"""
Repository for `data_source_connections` (Shopify et al.) — the one
collection in this codebase that must NEVER be returned to a caller
un-sanitized, because it holds a live external API credential. Every
function that could end up in an HTTP response strips `credentials_json`;
only `get_connection_with_credentials` (used exclusively by the sync job,
never by a route handler) returns the real thing.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.db.repositories import (
    create_business_scoped_document,
    get_business_scoped,
    list_business_scoped,
    update_business_scoped_document,
)

COLLECTION = "data_source_connections"


def _sanitize(doc: dict) -> dict:
    return {
        "id": doc["$id"],
        "provider": doc["provider"],
        "display_name": doc["display_name"],
        "status": doc.get("status", "connected"),
        "last_error": doc.get("last_error"),
        "last_synced_at": doc.get("last_synced_at"),
        "created_at": doc.get("$createdAt"),
    }


def create_connection(
    *, business_id: str, team_id: str, user_id: str, provider: str, display_name: str, credentials: dict[str, Any]
) -> dict:
    doc = create_business_scoped_document(
        COLLECTION, business_id, team_id,
        data={
            "provider": provider,
            "display_name": display_name,
            "credentials_json": json.dumps(credentials),
            "status": "connected",
            "created_by_user_id": user_id,
        },
    )
    return _sanitize(doc)


def list_connections(team_id: str, business_id: str) -> list[dict]:
    # list_business_scoped already filters by team_id; the business_id
    # query is an extra belt-and-suspenders check since a team currently
    # maps 1:1 to a business, but this stays correct if that ever changes.
    from appwrite.query import Query
    docs = list_business_scoped(COLLECTION, team_id, queries=[Query.equal("business_id", business_id)])
    return [_sanitize(d) for d in docs]


def get_connection_with_credentials(team_id: str, connection_id: str) -> dict | None:
    """Internal use only (sync job) — includes the raw credentials. Never return this from a route handler."""
    doc = get_business_scoped(COLLECTION, connection_id, team_id)
    if doc is None:
        return None
    credentials = json.loads(doc["credentials_json"]) if doc.get("credentials_json") else {}
    return {**doc, "credentials": credentials}


def mark_sync_success(team_id: str, connection_id: str) -> None:
    update_business_scoped_document(
        COLLECTION, connection_id, team_id,
        {"status": "connected", "last_error": None, "last_synced_at": datetime.now(timezone.utc).isoformat()},
    )


def mark_sync_error(team_id: str, connection_id: str, message: str) -> None:
    update_business_scoped_document(COLLECTION, connection_id, team_id, {"status": "error", "last_error": message[:1000]})


def delete_connection(team_id: str, connection_id: str) -> bool:
    from app.db.client import get_databases
    from app.db.schema import DATABASE_ID

    existing = get_business_scoped(COLLECTION, connection_id, team_id)
    if existing is None:
        return False
    get_databases().delete_document(DATABASE_ID, COLLECTION, connection_id)
    return True
