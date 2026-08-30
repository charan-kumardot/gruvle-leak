"""
Verifies dataset deletion and full account deletion actually work against
the live Appwrite project — these are destructive, irreversible operations
(spec section 12), so they get their own dedicated live test rather than
riding along inside an unrelated test's cleanup logic.
"""
from __future__ import annotations

import uuid

import pytest
from appwrite.id import ID
from fastapi.testclient import TestClient

from app.core.config import get_settings

settings = get_settings()
pytestmark = pytest.mark.integration

if not settings.appwrite_configured:
    pytest.skip("APPWRITE_PROJECT_ID / APPWRITE_API_KEY not set — skipping live end-to-end test.",
                allow_module_level=True)

from app.db.client import get_databases, get_users
from app.db.repositories import create_business, get_teams
from app.db.schema import DATABASE_ID
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Internal-Token": settings.worker_api_internal_token}


def _make_user_and_business(label: str):
    users = get_users()
    user_id = ID.unique()
    unique = uuid.uuid4().hex[:10]
    users.create(user_id=user_id, email=f"{label}-{unique}@example.invalid", name=label)
    business = create_business(user_id=user_id, name=f"{label} business", currency="INR")
    return user_id, business["$id"], business["team_id"]


def test_dataset_deletion_removes_dataset_columns_and_mappings(client: TestClient, auth_headers: dict):
    databases = get_databases()
    teams = get_teams()
    users = get_users()
    user_id, business_id, team_id = _make_user_and_business("dataset-delete-test")

    try:
        upload_resp = client.post(
            "/datasets/upload", headers=auth_headers,
            files={"file": ("orders.csv", b"order_id,status,total_amount\nO1,completed,100\n", "text/csv")},
            data={"business_id": business_id, "team_id": team_id},
        )
        assert upload_resp.status_code == 200, upload_resp.text
        dataset_id = upload_resp.json()["dataset_id"]

        list_resp = client.get("/datasets", headers=auth_headers, params={"business_id": business_id, "team_id": team_id})
        assert list_resp.status_code == 200
        assert any(d["id"] == dataset_id for d in list_resp.json()["datasets"])

        delete_resp = client.delete(f"/datasets/{dataset_id}", headers=auth_headers, params={"team_id": team_id})
        assert delete_resp.status_code == 200, delete_resp.text

        # Gone from the list, and its columns/mappings are gone too
        list_resp_2 = client.get("/datasets", headers=auth_headers, params={"business_id": business_id, "team_id": team_id})
        assert not any(d["id"] == dataset_id for d in list_resp_2.json()["datasets"])

        from appwrite.query import Query
        for coll in ("dataset_columns", "data_mappings"):
            remaining = databases.list_documents(DATABASE_ID, coll, [Query.equal("dataset_id", dataset_id)])
            docs = remaining.documents if hasattr(remaining, "documents") else remaining["documents"]
            assert docs == []

        # Deleting again is a clean 404, not a crash
        delete_again = client.delete(f"/datasets/{dataset_id}", headers=auth_headers, params={"team_id": team_id})
        assert delete_again.status_code == 404
    finally:
        try:
            databases.delete_document(DATABASE_ID, "businesses", business_id)
        except Exception:
            pass
        try:
            teams.delete(team_id)
        except Exception:
            pass
        try:
            users.delete(user_id)
        except Exception:
            pass


def test_full_account_deletion_cascades_everything(client: TestClient, auth_headers: dict):
    databases = get_databases()
    teams = get_teams()
    users = get_users()
    user_id, business_id, team_id = _make_user_and_business("account-delete-test")

    upload_resp = client.post(
        "/datasets/upload", headers=auth_headers,
        files={"file": ("orders.csv", b"order_id,status,total_amount\nO1,completed,100\n", "text/csv")},
        data={"business_id": business_id, "team_id": team_id},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    dataset_id = upload_resp.json()["dataset_id"]

    scan_resp = client.post(
        "/scans", headers=auth_headers,
        json={"business_id": business_id, "team_id": team_id, "created_by_user_id": user_id,
              "dataset_ids": [dataset_id], "currency": "INR"},
    )
    assert scan_resp.status_code == 200, scan_resp.text

    delete_resp = client.post(
        "/account/delete", headers=auth_headers,
        json={"business_id": business_id, "team_id": team_id, "user_id": user_id},
    )
    assert delete_resp.status_code == 200, delete_resp.text

    # Business document is gone
    from appwrite.exception import AppwriteException
    with pytest.raises(AppwriteException):
        databases.get_document(DATABASE_ID, "businesses", business_id)

    # Team is gone
    with pytest.raises(AppwriteException):
        teams.get(team_id)

    # User is gone
    with pytest.raises(AppwriteException):
        users.get(user_id)

    # Datasets/scans for this business are gone
    from appwrite.query import Query
    for coll in ("datasets", "scans", "leak_findings"):
        remaining = databases.list_documents(DATABASE_ID, coll, [Query.equal("business_id", business_id)])
        docs = remaining.documents if hasattr(remaining, "documents") else remaining["documents"]
        assert docs == [], f"{coll} still has documents after account deletion"
