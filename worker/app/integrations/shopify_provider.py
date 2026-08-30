"""
Shopify integration — pulls orders straight from a merchant's store via the
Admin REST API.

Deliberately uses a **Custom App Admin API access token**, not OAuth. A
merchant generates this themselves, in about a minute, from their own
Shopify admin (Settings -> Apps and sales channels -> Develop apps ->
Create an app -> Configure Admin API scopes: read_orders, read_products,
read_customers -> Install app -> reveal the Admin API access token). This
is the standard Shopify-recommended path for a private, single-store
integration and needs no app-review process on our side — unlike a public
OAuth app, which would require Shopify to review and approve Gruvle Leak
before any merchant could connect it. If Gruvle later lists in the Shopify
App Store, this provider's `fetch_orders` logic is unchanged — only how
`credentials["access_token"]` gets populated (OAuth flow vs. pasted token)
would need to change, behind this same interface.

Order-to-row mapping (spec: never fabricate — every field here traces to
a real Shopify API field, documented at each mapping):
  order_id        -> Shopify order "name" (e.g. "#1001"), the number a
                      merchant actually recognizes
  customer_id     -> Shopify customer id, falling back to the order email
  status          -> "cancelled" if cancelled_at is set, else "completed"
                      if fulfillment_status == "fulfilled", else "pending"
  total_amount    -> order.total_price (Shopify's own tax-inclusive total)
  order_date      -> order.created_at, date part only
  currency        -> order.currency

Line-item detail (product_id/unit_price/quantity/discount_amount) is only
populated when an order has exactly one line item — with multiple line
items we'd have to either explode one Shopify order into several detector
rows (breaking the 1:1 order_id join UnbilledRevenueDetector and
InvoiceMismatchDetector rely on) or silently average across dissimilar
products (misleading for PricingLeakDetector). Rather than guess, orders
with multiple line items simply carry no product_id, and a warning on the
resulting ParsedTable says so — the same "detector cleanly skips rather
than fabricates" principle applied everywhere else in this codebase.
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import httpx

from app.integrations.base import DataSourceConnectionError, DataSourceProvider
from app.parsers.base import ParsedTable

API_VERSION = "2024-10"
PAGE_LIMIT = 250
MAX_ORDERS = 1000  # bounded for MVP request latency, matching the 10MB-file-scale target elsewhere


def _normalize_shop_domain(raw: str) -> str:
    domain = raw.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.rstrip("/")
    if not domain.endswith(".myshopify.com"):
        domain = f"{domain}.myshopify.com"
    return domain


def _next_page_info(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' not in part:
            continue
        match = re.search(r"page_info=([^&>]+)", part)
        if match:
            return match.group(1)
    return None


def _to_decimal_str(value) -> str | None:
    if value is None:
        return None
    try:
        return str(Decimal(str(value)))
    except InvalidOperation:
        return None


class ShopifyProvider(DataSourceProvider):
    key = "shopify"
    label = "Shopify"

    def _base_url(self, shop_domain: str) -> str:
        return f"https://{_normalize_shop_domain(shop_domain)}/admin/api/{API_VERSION}"

    async def test_connection(self, credentials: dict) -> str:
        shop_domain = credentials.get("shop_domain", "")
        access_token = credentials.get("access_token", "")
        if not shop_domain or not access_token:
            raise DataSourceConnectionError("Both a shop domain and an Admin API access token are required.")

        url = f"{self._base_url(shop_domain)}/shop.json"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers={"X-Shopify-Access-Token": access_token})
        except httpx.HTTPError as e:
            raise DataSourceConnectionError(f"Could not reach {shop_domain}: {e}") from e

        if resp.status_code == 401:
            raise DataSourceConnectionError(
                "Shopify rejected this access token. Double-check you copied the full Admin API access token "
                "(starts with 'shpat_') from your custom app's API credentials page."
            )
        if resp.status_code == 404:
            raise DataSourceConnectionError(f"Shop '{shop_domain}' was not found — check the domain for typos.")
        if resp.status_code != 200:
            raise DataSourceConnectionError(f"Shopify returned an unexpected error ({resp.status_code}).")

        try:
            shop_name = resp.json()["shop"]["name"]
        except (KeyError, ValueError) as e:
            raise DataSourceConnectionError("Connected, but Shopify's response wasn't in the expected shape.") from e
        return shop_name

    async def fetch_orders(self, credentials: dict, since: datetime | None = None) -> ParsedTable:
        shop_domain = credentials.get("shop_domain", "")
        access_token = credentials.get("access_token", "")
        if not shop_domain or not access_token:
            raise DataSourceConnectionError("Both a shop domain and an Admin API access token are required.")

        headers = {"X-Shopify-Access-Token": access_token}
        params = {
            "status": "any",
            "limit": str(PAGE_LIMIT),
            "order": "created_at desc",
        }
        if since is not None:
            params["created_at_min"] = since.isoformat()

        url = f"{self._base_url(shop_domain)}/orders.json"
        rows: list[dict] = []
        warnings: list[str] = []
        multi_line_item_count = 0

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                while url and len(rows) < MAX_ORDERS:
                    resp = await client.get(url, headers=headers, params=params)
                    if resp.status_code == 401:
                        raise DataSourceConnectionError("Shopify access token is no longer valid — reconnect this store.")
                    if resp.status_code != 200:
                        raise DataSourceConnectionError(f"Shopify returned an unexpected error ({resp.status_code}).")

                    payload = resp.json()
                    for order in payload.get("orders", []):
                        row, had_multi = self._map_order(order)
                        if had_multi:
                            multi_line_item_count += 1
                        rows.append(row)

                    next_page_info = _next_page_info(resp.headers.get("Link"))
                    if next_page_info and len(rows) < MAX_ORDERS:
                        url = f"{self._base_url(shop_domain)}/orders.json"
                        params = {"limit": str(PAGE_LIMIT), "page_info": next_page_info}
                    else:
                        url = None
        except httpx.HTTPError as e:
            raise DataSourceConnectionError(f"Lost connection to Shopify while fetching orders: {e}") from e

        if multi_line_item_count:
            warnings.append(
                f"{multi_line_item_count} order(s) had more than one line item — product-level pricing fields "
                "were left blank for those orders rather than guessed at (order-level total_amount is still accurate)."
            )
        if len(rows) >= MAX_ORDERS:
            warnings.append(f"Only the {MAX_ORDERS} most recent orders were pulled for this sync.")

        columns = [
            "order_id", "customer_id", "status", "total_amount", "order_date", "currency",
            "product_id", "unit_price", "quantity", "discount_amount",
        ]
        return ParsedTable(columns=columns, rows=rows, warnings=warnings)

    def _map_order(self, order: dict) -> tuple[dict, bool]:
        status = "pending"
        if order.get("cancelled_at"):
            status = "cancelled"
        elif order.get("fulfillment_status") == "fulfilled":
            status = "completed"

        customer = order.get("customer") or {}
        customer_id = str(customer.get("id") or order.get("email") or order.get("contact_email") or "unknown")

        row: dict = {
            "order_id": order.get("name") or str(order.get("id")),
            "customer_id": customer_id,
            "status": status,
            "total_amount": _to_decimal_str(order.get("total_price")) or "0",
            "order_date": (order.get("created_at") or "")[:10],
            "currency": order.get("currency") or "",
        }

        line_items = order.get("line_items") or []
        had_multi = len(line_items) > 1
        if len(line_items) == 1:
            item = line_items[0]
            qty = item.get("quantity") or 1
            unit_price = _to_decimal_str(item.get("price"))
            row["product_id"] = item.get("sku") or item.get("title") or "UNKNOWN"
            row["unit_price"] = unit_price
            row["quantity"] = str(qty)
            discount_total = sum(
                Decimal(str(d.get("amount", "0"))) for d in (item.get("discount_allocations") or [])
            )
            if discount_total > 0:
                row["discount_amount"] = str(discount_total)

        return row, had_multi
