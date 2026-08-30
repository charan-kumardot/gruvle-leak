"""
Multi-tenant data access layer for Gruvle Leak.

Isolation model
----------------
Every business in Gruvle Leak maps 1:1 to an Appwrite **Team** (its Team ID
is stored as `team_id` on the business's own `businesses` document, and is
denormalized onto every document of every business-owned collection — see
the note in `app/db/schema.py`). Every document belonging to a business is
created with document-level permissions scoped ONLY to that team:

    Permission.read(Role.team(team_id))
    Permission.update(Role.team(team_id))
    Permission.delete(Role.team(team_id))

No document created by this module is ever given `Role.any()` or
`Role.users()` permissions. Because every business-owned collection in
`schema.py` has `document_security=True`, Appwrite enforces these
permissions on every read/write made through a user's session or JWT: a
person who is not a member of a business's Team gets refused by Appwrite
itself, even if they somehow learn a document ID.

IMPORTANT — this module talks to Appwrite with the server API key
(`app/db/client.py: get_databases()`), and a server API key is NOT
constrained by document permissions the way an end-user session is. That
means the isolation guarantee for anything routed through this worker
service rests on THIS CODE filtering and re-checking `team_id` explicitly —
Appwrite's permission engine is what protects a different consumer (e.g. the
Next.js frontend using the Appwrite Web SDK with a real user session), not
the API-key-authenticated calls made here. `get_business_scoped` re-verifies
the returned document's stored `team_id` against the caller's expected team
and returns `None` — never raising, never revealing whether a document
exists to the wrong tenant — precisely because that check is doing real
security work here, not just acting as redundant defense-in-depth.

ALL code that creates a document in a business-owned collection MUST go
through `create_business_scoped_document()` (or a helper built on top of
it), and all business-scoped reads MUST go through `list_business_scoped`/
`get_business_scoped`. Never call `Databases.create_document`,
`list_documents`, or `get_document` directly against one of these
collections elsewhere in the codebase — doing so bypasses every guarantee
this module provides and is the single most likely way to introduce a
cross-tenant data leak (IDOR).
"""
from __future__ import annotations

from typing import Any

from appwrite.exception import AppwriteException
from appwrite.id import ID
from appwrite.permission import Permission
from appwrite.query import Query
from appwrite.role import Role
from appwrite.services.teams import Teams

from app.db.client import get_appwrite_client, get_databases
from app.db.schema import DATABASE_ID

HTTP_NOT_FOUND = 404


def get_teams() -> Teams:
    """Teams service client — one Appwrite Team per business (the tenant boundary)."""
    return Teams(get_appwrite_client())


def _flatten_document(document: Any) -> dict:
    """
    appwrite==23 models a returned document as system fields (`.id`,
    `.permissions`, ...) plus the collection's own attributes nested under a
    `.data` dict, rather than one flat dict. Flatten both into a single
    dict — `$id` / `$permissions` / ... alongside the custom fields — which
    matches the shape the raw Appwrite REST API returns and is what the rest
    of this module (and its tests) expect to work with.
    """
    if isinstance(document, dict):
        return dict(document)
    custom = document.data if isinstance(document.data, dict) else dict(document.data)
    return {
        **custom,
        "$id": document.id,
        "$collectionId": document.collectionid,
        "$databaseId": document.databaseid,
        "$createdAt": document.createdat,
        "$updatedAt": document.updatedat,
        "$permissions": document.permissions,
    }


def _team_permissions(team_id: str) -> list[str]:
    """
    The one and only permission set a business-owned document should ever be
    created with: read/update/delete scoped to the owning business's team,
    nothing broader.
    """
    return [
        Permission.read(Role.team(team_id)),
        Permission.update(Role.team(team_id)),
        Permission.delete(Role.team(team_id)),
    ]


def create_business(user_id: str, name: str, **extra_fields: Any) -> dict:
    """
    Provisions a brand-new business: one Appwrite Team (the tenant boundary)
    plus the `businesses` document describing it, with `user_id` added to
    the team as owner so subsequent team-scoped permission checks apply to
    them immediately.

    `extra_fields` may supply any other `businesses` attribute from
    schema.py (industry, currency, business_model, avg_order_value, ...).

    Returns the created `businesses` document as a plain dict.
    """
    teams = get_teams()
    databases = get_databases()

    team_id = ID.unique()
    teams.create(team_id=team_id, name=name, roles=["owner"])

    try:
        teams.create_membership(team_id=team_id, roles=["owner"], user_id=user_id)
    except AppwriteException:
        # Don't leave an orphaned, memberless team behind after a failed
        # provisioning attempt.
        try:
            teams.delete(team_id)
        except AppwriteException:
            pass
        raise

    data = {
        "owner_user_id": user_id,
        "team_id": team_id,
        "name": name,
        **extra_fields,
    }

    try:
        document = databases.create_document(
            database_id=DATABASE_ID,
            collection_id="businesses",
            document_id=ID.unique(),
            data=data,
            permissions=_team_permissions(team_id),
        )
    except AppwriteException:
        # Same rollback rationale as above — no document means no business,
        # so don't leave its team behind either.
        try:
            teams.delete(team_id)
        except AppwriteException:
            pass
        raise

    return _flatten_document(document)


def create_business_scoped_document(
    collection_id: str,
    business_id: str,
    team_id: str,
    data: dict[str, Any],
    document_id: str | None = None,
) -> dict:
    """
    The single entry point every business-owned collection (datasets, scans,
    leak_findings, ...) must route document creation through. Always stamps
    `business_id` and `team_id` onto the document and always applies the
    team-scoped permission set from `_team_permissions` — no caller can opt
    out of isolation by calling this with different permissions, because
    none are accepted as a parameter.
    """
    databases = get_databases()
    payload = {**data, "business_id": business_id, "team_id": team_id}
    document = databases.create_document(
        database_id=DATABASE_ID,
        collection_id=collection_id,
        document_id=document_id or ID.unique(),
        data=payload,
        permissions=_team_permissions(team_id),
    )
    return _flatten_document(document)


def list_business_scoped(
    collection_id: str,
    team_id: str,
    queries: list[str] | None = None,
) -> list[dict]:
    """
    Lists documents in a business-owned collection, always filtered to the
    caller's `team_id`. This filter is load-bearing, not cosmetic: the
    server API key used here is not itself restricted by document
    permissions, so omitting it would return every tenant's documents.
    """
    databases = get_databases()
    all_queries = [Query.equal("team_id", team_id)] + list(queries or [])
    result = databases.list_documents(
        database_id=DATABASE_ID,
        collection_id=collection_id,
        queries=all_queries,
    )
    documents = result.get("documents") if isinstance(result, dict) else getattr(result, "documents", [])
    return [_flatten_document(d) for d in documents]


def update_business_scoped_document(
    collection_id: str,
    document_id: str,
    expected_team_id: str,
    data: dict[str, Any],
) -> dict | None:
    """
    Updates a document only after verifying (via `get_business_scoped`) that
    it belongs to `expected_team_id` — the same ownership re-check
    `get_business_scoped` performs for reads, applied before any write.
    Returns `None` (without writing anything) if the document doesn't exist
    or belongs to a different tenant.
    """
    existing = get_business_scoped(collection_id, document_id, expected_team_id)
    if existing is None:
        return None

    databases = get_databases()
    document = databases.update_document(
        database_id=DATABASE_ID,
        collection_id=collection_id,
        document_id=document_id,
        data=data,
    )
    return _flatten_document(document)


def get_business_scoped(
    collection_id: str,
    document_id: str,
    expected_team_id: str,
) -> dict | None:
    """
    Fetches a single document and verifies it actually belongs to
    `expected_team_id` before returning it. Returns `None` — never raises,
    never distinguishes "doesn't exist" from "belongs to someone else" — if
    the document is missing or owned by a different tenant, so a caller
    can't probe for the existence of another business's records via error
    behavior.
    """
    databases = get_databases()
    try:
        document = databases.get_document(
            database_id=DATABASE_ID,
            collection_id=collection_id,
            document_id=document_id,
        )
    except AppwriteException as e:
        if getattr(e, "code", None) == HTTP_NOT_FOUND:
            return None
        raise

    doc = _flatten_document(document)
    if doc.get("team_id") != expected_team_id:
        return None
    return doc
