"""
Registry of DataSourceProviders. Follows the same "real implementations
plus honest stubs" pattern as `app/detectors/registry.py` — every provider
key the product will eventually support is listed here (spec section 89),
but only the ones with a real implementation are usable; the rest raise a
clear NotImplementedError explaining exactly what's missing, so the API
and UI can show every planned integration without pretending an
unimplemented one works.
"""
from __future__ import annotations

from app.integrations.base import DataSourceProvider
from app.integrations.shopify_provider import ShopifyProvider


class _NotYetImplemented(DataSourceProvider):
    def __init__(self, key: str, label: str, reason: str):
        self.key = key
        self.label = label
        self._reason = reason

    async def test_connection(self, credentials: dict) -> str:
        raise NotImplementedError(self._reason)

    async def fetch_orders(self, credentials: dict, since=None):
        raise NotImplementedError(self._reason)


PROVIDERS: dict[str, DataSourceProvider] = {
    "shopify": ShopifyProvider(),
    "hubspot": _NotYetImplemented(
        "hubspot", "HubSpot",
        "Not yet implemented. HubSpot supports Private App API keys (no OAuth review needed, same "
        "pattern as Shopify) — the connector logic just hasn't been written yet.",
    ),
    "quickbooks": _NotYetImplemented(
        "quickbooks", "QuickBooks",
        "Not yet implemented. QuickBooks requires a registered Intuit OAuth app and goes through "
        "Intuit's app review for production access — needs that setup before a connector can be built.",
    ),
    "zoho": _NotYetImplemented(
        "zoho", "Zoho Books",
        "Not yet implemented. Zoho supports self-client OAuth credentials a business can generate "
        "themselves (similar to Shopify's custom-app model) — the connector logic hasn't been written yet.",
    ),
    "salesforce": _NotYetImplemented(
        "salesforce", "Salesforce",
        "Not yet implemented. Requires a registered Salesforce Connected App; a business admin can "
        "create one in their own org without Salesforce's review, but the connector logic hasn't been written yet.",
    ),
}


def get_provider(key: str) -> DataSourceProvider:
    provider = PROVIDERS.get(key)
    if provider is None:
        raise KeyError(f"Unknown data source provider: {key}")
    return provider


def list_providers() -> list[dict]:
    return [
        {"key": p.key, "label": p.label, "available": p.key == "shopify"}
        for p in PROVIDERS.values()
    ]
