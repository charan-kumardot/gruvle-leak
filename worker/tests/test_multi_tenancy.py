"""
Integration test against the LIVE Appwrite project configured in `worker/.env`
(spec section 57 / 58: a user from Business A must never be able to read
Business B's data, including by guessing an ID). Skips cleanly if Appwrite
isn't configured — these are not unit tests, they hit real network calls.

Creates two real businesses (two Teams + two `businesses` documents) and a
real `datasets` document under Business A, then asserts:
  1. `get_business_scoped` refuses to return Business A's document when
     asked for it under Business B's team_id (the repository-layer check
     that matters for this worker service, which talks to Appwrite with a
     privileged API key not itself constrained by document permissions).
  2. The document's own Appwrite permissions array never grants Business B's
     team, `any`, or `users` access (the guarantee Appwrite's permission
     engine enforces for any OTHER consumer, e.g. the web app's end-user
     sessions).

Everything created here is cleaned up in a `finally` block.
"""
from __future__ import annotations

import pytest

from app.core.config import get_settings

settings = get_settings()

pytestmark = pytest.mark.integration

if not settings.appwrite_configured:
    pytest.skip("APPWRITE_PROJECT_ID / APPWRITE_API_KEY not set — skipping live Appwrite integration test.",
                allow_module_level=True)

import uuid

from appwrite.id import ID

from app.db.repositories import create_business, create_business_scoped_document, get_business_scoped, get_teams
from app.db.client import get_databases, get_users
from app.db.schema import DATABASE_ID


def _make_test_user(label: str) -> str:
    """create_business requires a real Appwrite user id (Teams.create_membership
    validates it exists) — provision a throwaway one via the server Users API."""
    users = get_users()
    user_id = ID.unique()
    unique = uuid.uuid4().hex[:10]
    users.create(user_id=user_id, email=f"multitenancy-test-{unique}@example.invalid", name=label)
    return user_id


def test_cross_tenant_read_is_refused():
    databases = get_databases()
    teams = get_teams()
    users = get_users()

    user_a = _make_test_user("Test User A")
    user_b = _make_test_user("Test User B")

    business_a = create_business(user_id=user_a, name="Test Business A (multi-tenancy test)")
    business_b = create_business(user_id=user_b, name="Test Business B (multi-tenancy test)")

    dataset_doc = None
    try:
        dataset_doc = create_business_scoped_document(
            collection_id="datasets",
            business_id=business_a["$id"],
            team_id=business_a["team_id"],
            data={
                "kind": "ORDERS",
                "original_filename": "multi-tenancy-test.csv",
                "file_type": "csv",
                "file_size_bytes": 10,
                "storage_file_id": "test-file-id",
            },
        )

        # 1. Repository-layer isolation: Business B's team_id must not unlock Business A's document.
        as_seen_by_b = get_business_scoped("datasets", dataset_doc["$id"], expected_team_id=business_b["team_id"])
        assert as_seen_by_b is None

        # Sanity check: the same lookup DOES succeed under the correct team_id,
        # so the None above is the isolation check working, not a broken getter.
        as_seen_by_a = get_business_scoped("datasets", dataset_doc["$id"], expected_team_id=business_a["team_id"])
        assert as_seen_by_a is not None
        assert as_seen_by_a["$id"] == dataset_doc["$id"]

        # 2. Appwrite-permission-layer isolation: the document's own permissions
        # never grant Business B's team, and never grant `any` or `users`.
        permissions = dataset_doc.get("$permissions", [])
        assert not any(business_b["team_id"] in p for p in permissions)
        assert not any(p.startswith("read(\"any\"") or p == 'read("any")' for p in permissions)
        assert not any('role:"users"' in p or 'users("' in p for p in permissions)
        assert any(business_a["team_id"] in p for p in permissions)

    finally:
        if dataset_doc is not None:
            try:
                databases.delete_document(DATABASE_ID, "datasets", dataset_doc["$id"])
            except Exception:
                pass
        for business in (business_a, business_b):
            try:
                databases.delete_document(DATABASE_ID, "businesses", business["$id"])
            except Exception:
                pass
            try:
                teams.delete(business["team_id"])
            except Exception:
                pass
        for user_id in (user_a, user_b):
            try:
                users.delete(user_id)
            except Exception:
                pass
