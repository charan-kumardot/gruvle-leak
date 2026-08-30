"""
Full end-to-end integration test against the LIVE Appwrite project: real
HTTP requests through the actual FastAPI app, real file upload, real
parsing/profiling/mapping, real detection, real persistence, real report
export — the same path a production request takes. Skips cleanly if
Appwrite isn't configured.
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

ORDERS_CSV = (
    "order_id,customer_id,status,total_amount,order_date,currency\n"
    "ORDER-1,CUST-1,completed,25000,2026-01-05,INR\n"
    "ORDER-2,CUST-2,completed,10000,2026-01-06,INR\n"
    "ORDER-3,CUST-3,pending,5000,2026-01-07,INR\n"
)
INVOICES_CSV = (
    "invoice_id,order_id,customer_id,total_amount,invoice_date,currency\n"
    "INV-1,ORDER-2,CUST-2,10000,2026-01-07,INR\n"
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Internal-Token": settings.worker_api_internal_token}


def test_upload_scan_findings_report_end_to_end(client: TestClient, auth_headers: dict):
    databases = get_databases()
    teams = get_teams()
    users = get_users()

    user_id = ID.unique()
    unique = uuid.uuid4().hex[:10]
    users.create(user_id=user_id, email=f"scan-pipeline-test-{unique}@example.invalid", name="Scan Pipeline Test User")
    business = create_business(user_id=user_id, name="Scan Pipeline Test Business", currency="INR")
    business_id, team_id = business["$id"], business["team_id"]

    dataset_ids: list[str] = []
    scan_id = None
    try:
        orders_resp = client.post(
            "/datasets/upload", headers=auth_headers,
            files={"file": ("orders.csv", ORDERS_CSV.encode(), "text/csv")},
            data={"business_id": business_id, "team_id": team_id},
        )
        assert orders_resp.status_code == 200, orders_resp.text
        orders_result = orders_resp.json()
        dataset_ids.append(orders_result["dataset_id"])
        assert orders_result["row_count"] == 3
        assert orders_result["kind"] == "ORDERS"
        total_mapped = [m for m in orders_result["mapping"] if m["canonical_field"] == "total_amount"]
        assert total_mapped and total_mapped[0]["confidence"] > 0

        invoices_resp = client.post(
            "/datasets/upload", headers=auth_headers,
            files={"file": ("invoices.csv", INVOICES_CSV.encode(), "text/csv")},
            data={"business_id": business_id, "team_id": team_id},
        )
        assert invoices_resp.status_code == 200, invoices_resp.text
        invoices_result = invoices_resp.json()
        dataset_ids.append(invoices_result["dataset_id"])
        assert invoices_result["kind"] == "INVOICES"

        scan_resp = client.post(
            "/scans", headers=auth_headers,
            json={"business_id": business_id, "team_id": team_id, "created_by_user_id": user_id,
                  "dataset_ids": dataset_ids, "currency": "INR"},
        )
        assert scan_resp.status_code == 200, scan_resp.text
        scan_summary = scan_resp.json()
        scan_id = scan_summary["scan_id"]

        assert scan_summary["finding_count"] >= 1
        unbilled = [f for f in scan_summary["all_findings"] if f["category"] == "UNBILLED"]
        assert len(unbilled) == 1
        assert unbilled[0]["financial_impact"]["amount"] == "25000"  # ORDER-1, completed, never invoiced
        assert unbilled[0]["evidence"], "finding must carry evidence, not just a number"

        # GET /scans/:id reflects the completed stage
        status_resp = client.get(f"/scans/{scan_id}", headers=auth_headers, params={"team_id": team_id})
        assert status_resp.status_code == 200
        assert status_resp.json()["stage"] == "COMPLETED"

        # GET /scans/:id/findings returns the persisted findings
        findings_resp = client.get(f"/scans/{scan_id}/findings", headers=auth_headers, params={"team_id": team_id})
        assert findings_resp.status_code == 200
        findings = findings_resp.json()
        assert len(findings) == scan_summary["finding_count"]
        finding_id = findings[0]["id"]

        # GET /findings/:id returns the same finding with evidence + calculation
        finding_resp = client.get(f"/findings/{finding_id}", headers=auth_headers, params={"team_id": team_id})
        assert finding_resp.status_code == 200
        assert finding_resp.json()["calculation"]["result"]

        # A user cannot read this finding under a different team_id (IDOR check)
        wrong_team_resp = client.get(f"/findings/{finding_id}", headers=auth_headers, params={"team_id": "not-my-team"})
        assert wrong_team_resp.status_code == 404

        # POST /findings/:id/status confirms it
        confirm_resp = client.post(
            f"/findings/{finding_id}/status", headers=auth_headers,
            json={"team_id": team_id, "status": "CONFIRMED"},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "CONFIRMED"

        # Report exports all work off the same persisted data
        for fmt, expect_prefix in (("pdf", b"%PDF"), ("csv", None), ("markdown", None), ("json", None)):
            report_resp = client.get(f"/scans/{scan_id}/report", headers=auth_headers,
                                      params={"team_id": team_id, "format": fmt})
            assert report_resp.status_code == 200
            if expect_prefix:
                assert report_resp.content[:4] == expect_prefix

        # Missing internal token is refused
        no_token_resp = client.get(f"/scans/{scan_id}", params={"team_id": team_id})
        assert no_token_resp.status_code == 401

    finally:
        from appwrite.query import Query

        for dataset_id in dataset_ids:
            try:
                for coll in ("dataset_columns", "data_mappings"):
                    for doc in databases.list_documents(DATABASE_ID, coll, [Query.equal("dataset_id", dataset_id)])["documents"]:
                        databases.delete_document(DATABASE_ID, coll, doc["$id"])
                databases.delete_document(DATABASE_ID, "datasets", dataset_id)
            except Exception:
                pass
        if scan_id:
            try:
                finding_docs = databases.list_documents(
                    DATABASE_ID, "leak_findings", [Query.equal("scan_id", scan_id)]
                )["documents"]
                for finding_doc in finding_docs:
                    for coll in ("leak_evidence", "leak_calculations"):
                        for doc in databases.list_documents(
                            DATABASE_ID, coll, [Query.equal("finding_id", finding_doc["$id"])]
                        )["documents"]:
                            databases.delete_document(DATABASE_ID, coll, doc["$id"])
                    databases.delete_document(DATABASE_ID, "leak_findings", finding_doc["$id"])
                databases.delete_document(DATABASE_ID, "scans", scan_id)
            except Exception:
                pass
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
