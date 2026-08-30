"""
Full connect -> sync -> scan pipeline against the LIVE Appwrite project,
proving a Shopify connection's data flows through the exact same
ingestion/detection/persistence path a manual CSV upload does. Shopify's
own HTTP API is mocked (no real store available in CI) — everything after
that (Appwrite writes, profiling, mapping, detection, scoring) is real.
Skips cleanly if Appwrite isn't configured.
"""
from __future__ import annotations

import uuid

import httpx
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
from app.db.repositories import create_business, get_business_scoped, get_teams
from app.db.schema import DATABASE_ID
from app.main import app

SHOPIFY_ORDERS_PAGE = {
    "orders": [
        {
            "id": 1, "name": "#5001", "total_price": "40000.00", "currency": "INR",
            "created_at": "2026-01-10T10:00:00-05:00", "fulfillment_status": "fulfilled", "cancelled_at": None,
            "customer": {"id": 900}, "email": "a@example.com",
            "line_items": [{"sku": "WIDGET", "price": "40000.00", "quantity": "1", "discount_allocations": []}],
        },
        {
            "id": 2, "name": "#5002", "total_price": "9000.00", "currency": "INR",
            "created_at": "2026-01-11T10:00:00-05:00", "fulfillment_status": None, "cancelled_at": None,
            "customer": {"id": 901}, "email": "b@example.com", "line_items": [],
        },
    ]
}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Internal-Token": settings.worker_api_internal_token}


@pytest.fixture(autouse=True)
def mock_shopify_http(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if "shop.json" in str(request.url):
            return httpx.Response(200, json={"shop": {"name": "Mock Test Store"}})
        return httpx.Response(200, json=SHOPIFY_ORDERS_PAGE, headers={})

    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


def test_shopify_connect_sync_and_scan_end_to_end(client: TestClient, auth_headers: dict):
    databases = get_databases()
    teams = get_teams()
    users = get_users()

    user_id = ID.unique()
    unique = uuid.uuid4().hex[:10]
    users.create(user_id=user_id, email=f"shopify-sync-test-{unique}@example.invalid", name="Shopify Sync Test")
    business = create_business(user_id=user_id, name="Shopify Sync Test Business", currency="INR")
    business_id, team_id = business["$id"], business["team_id"]

    connection_id = None
    dataset_id = None
    scan_id = None
    try:
        # 1. Connect
        connect_resp = client.post(
            "/integrations/connections", headers=auth_headers,
            json={
                "business_id": business_id, "team_id": team_id, "user_id": user_id, "provider": "shopify",
                "credentials": {"shop_domain": "mock-test-store", "access_token": "shpat_mock"},
            },
        )
        assert connect_resp.status_code == 200, connect_resp.text
        connection = connect_resp.json()
        connection_id = connection["id"]
        assert connection["display_name"] == "Mock Test Store"
        assert connection["status"] == "connected"
        assert "credentials" not in connection and "credentials_json" not in connection

        # 2. List connections — sanitized
        list_resp = client.get("/integrations/connections", headers=auth_headers,
                                params={"business_id": business_id, "team_id": team_id})
        assert list_resp.status_code == 200
        assert len(list_resp.json()["connections"]) == 1

        # 3. Sync — pulls the (mocked) Shopify orders through the real ingestion pipeline
        sync_resp = client.post(
            f"/integrations/connections/{connection_id}/sync", headers=auth_headers,
            json={"business_id": business_id, "team_id": team_id},
        )
        assert sync_resp.status_code == 200, sync_resp.text
        sync_result = sync_resp.json()
        dataset_id = sync_result["dataset_id"]
        assert sync_result["row_count"] == 2
        assert sync_result["kind"] == "ORDERS"

        # The dataset document must record where it came from
        dataset_doc = get_business_scoped("datasets", dataset_id, team_id)
        assert dataset_doc["source"] == "shopify"
        assert dataset_doc["source_connection_id"] == connection_id

        # 4. Scan the synced dataset — same detectors, same scoring, same persistence as a manual upload
        scan_resp = client.post(
            "/scans", headers=auth_headers,
            json={"business_id": business_id, "team_id": team_id, "created_by_user_id": user_id,
                  "dataset_ids": [dataset_id], "currency": "INR"},
        )
        assert scan_resp.status_code == 200, scan_resp.text
        scan_summary = scan_resp.json()
        scan_id = scan_summary["scan_id"]

        # Order #5001 (₹40,000, fulfilled -> "completed") has no invoices dataset at all,
        # so UnbilledRevenueDetector should cleanly skip rather than fabricate a finding —
        # this scan only had one dataset (orders), matching a Shopify-only connection with
        # no separate invoicing system.
        assert scan_summary["finding_count"] == 0
        detectors_skipped_text = " ".join(scan_summary["detectors_skipped"])
        assert "UnbilledRevenueDetector" in detectors_skipped_text

    finally:
        from appwrite.query import Query
        if dataset_id:
            try:
                for coll in ("dataset_columns", "data_mappings"):
                    for doc in databases.list_documents(DATABASE_ID, coll, [Query.equal("dataset_id", dataset_id)])["documents"]:
                        databases.delete_document(DATABASE_ID, coll, doc["$id"])
                databases.delete_document(DATABASE_ID, "datasets", dataset_id)
            except Exception:
                pass
        if scan_id:
            try:
                databases.delete_document(DATABASE_ID, "scans", scan_id)
            except Exception:
                pass
        if connection_id:
            try:
                databases.delete_document(DATABASE_ID, "data_source_connections", connection_id)
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
