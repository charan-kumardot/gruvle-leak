"""
Tests the Shopify provider's mapping logic and pagination against a mocked
Shopify API (httpx.MockTransport — no real store needed, no new
dependency). What's NOT covered here: whether a real merchant's Custom App
token actually works end-to-end — that needs a live store, see
docs/INTEGRATIONS.md for how to get one and verify manually.
"""
from __future__ import annotations

import httpx
import pytest

from app.integrations.base import DataSourceConnectionError
from app.integrations.shopify_provider import ShopifyProvider, _normalize_shop_domain

CREDENTIALS = {"shop_domain": "my-test-store", "access_token": "shpat_fake_token"}


def _order(order_id: int, name: str, total: str, fulfillment_status=None, cancelled_at=None,
           line_items=None, created_at="2026-01-05T10:00:00-05:00"):
    return {
        "id": order_id, "name": name, "total_price": total, "currency": "INR",
        "created_at": created_at, "fulfillment_status": fulfillment_status, "cancelled_at": cancelled_at,
        "customer": {"id": 555}, "email": "buyer@example.com",
        "line_items": line_items or [],
    }


def test_normalize_shop_domain_accepts_various_formats():
    assert _normalize_shop_domain("my-store") == "my-store.myshopify.com"
    assert _normalize_shop_domain("https://my-store.myshopify.com/") == "my-store.myshopify.com"
    assert _normalize_shop_domain("MY-STORE.MYSHOPIFY.COM") == "my-store.myshopify.com"


@pytest.mark.asyncio
async def test_connection_success_returns_shop_name(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Shopify-Access-Token"] == "shpat_fake_token"
        assert "shop.json" in str(request.url)
        return httpx.Response(200, json={"shop": {"name": "My Test Store"}})

    _patch_client(monkeypatch, handler)
    provider = ShopifyProvider()
    name = await provider.test_connection(CREDENTIALS)
    assert name == "My Test Store"


@pytest.mark.asyncio
async def test_connection_bad_token_raises_clear_error(monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(401, json={}))
    provider = ShopifyProvider()
    with pytest.raises(DataSourceConnectionError, match="rejected this access token"):
        await provider.test_connection(CREDENTIALS)


@pytest.mark.asyncio
async def test_connection_missing_credentials_raises_before_any_request(monkeypatch):
    calls = []
    _patch_client(monkeypatch, lambda req: calls.append(req) or httpx.Response(200, json={}))
    provider = ShopifyProvider()
    with pytest.raises(DataSourceConnectionError):
        await provider.test_connection({"shop_domain": "x"})  # no access_token
    assert calls == []


@pytest.mark.asyncio
async def test_fetch_orders_maps_status_and_single_line_item(monkeypatch):
    orders_page = {
        "orders": [
            _order(1, "#1001", "1000.00", fulfillment_status="fulfilled",
                   line_items=[{"sku": "SKU-A", "price": "1000.00", "quantity": "1", "discount_allocations": []}]),
            _order(2, "#1002", "500.00", fulfillment_status=None),  # pending
            _order(3, "#1003", "250.00", cancelled_at="2026-01-06T00:00:00-05:00"),
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=orders_page, headers={})

    _patch_client(monkeypatch, handler)
    provider = ShopifyProvider()
    table = await provider.fetch_orders(CREDENTIALS)

    assert len(table.rows) == 3
    by_id = {r["order_id"]: r for r in table.rows}
    assert by_id["#1001"]["status"] == "completed"
    assert by_id["#1001"]["product_id"] == "SKU-A"
    assert by_id["#1001"]["unit_price"] == "1000.00"
    assert by_id["#1001"]["quantity"] == "1"
    assert by_id["#1002"]["status"] == "pending"
    assert by_id["#1003"]["status"] == "cancelled"
    assert by_id["#1001"]["total_amount"] == "1000.00"
    assert by_id["#1001"]["customer_id"] == "555"


@pytest.mark.asyncio
async def test_fetch_orders_multi_line_item_leaves_product_fields_blank_and_warns(monkeypatch):
    orders_page = {
        "orders": [
            _order(1, "#2001", "3000.00", fulfillment_status="fulfilled", line_items=[
                {"sku": "A", "price": "1000.00", "quantity": "1", "discount_allocations": []},
                {"sku": "B", "price": "2000.00", "quantity": "1", "discount_allocations": []},
            ]),
        ]
    }
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json=orders_page, headers={}))
    provider = ShopifyProvider()
    table = await provider.fetch_orders(CREDENTIALS)

    row = table.rows[0]
    assert "product_id" not in row
    assert row["total_amount"] == "3000.00"  # order-level total is still accurate
    assert any("more than one line item" in w for w in table.warnings)


@pytest.mark.asyncio
async def test_fetch_orders_follows_pagination_link_header(monkeypatch):
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(
                200,
                json={"orders": [_order(1, "#1", "100.00", fulfillment_status="fulfilled")]},
                headers={"Link": '<https://my-test-store.myshopify.com/admin/api/2024-10/orders.json?page_info=abc123&limit=250>; rel="next"'},
            )
        return httpx.Response(200, json={"orders": [_order(2, "#2", "200.00", fulfillment_status="fulfilled")]}, headers={})

    _patch_client(monkeypatch, handler)
    provider = ShopifyProvider()
    table = await provider.fetch_orders(CREDENTIALS)

    assert call_count["n"] == 2
    assert {r["order_id"] for r in table.rows} == {"#1", "#2"}


@pytest.mark.asyncio
async def test_fetch_orders_401_mid_sync_raises_clear_error(monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(401, json={}))
    provider = ShopifyProvider()
    with pytest.raises(DataSourceConnectionError, match="no longer valid"):
        await provider.fetch_orders(CREDENTIALS)


def _patch_client(monkeypatch, handler):
    """Redirects every httpx.AsyncClient created inside the provider to a MockTransport."""
    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
