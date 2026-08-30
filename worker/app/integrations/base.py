"""
DataSourceProvider abstraction — a live external system (Shopify, HubSpot,
QuickBooks, ...) that Gruvle can pull records from directly, instead of a
human exporting a CSV by hand.

Design principle: a provider's job ends at producing a `ParsedTable` — the
exact same shape `app/parsers/*` produce from an uploaded file. Everything
downstream (profiling, AI-assisted column mapping, storage, detection,
scoring, reporting) is untouched and already tested; a new integration is
just a new way to arrive at a `ParsedTable`, never a parallel pipeline.

Credentials are provider-specific and opaque to everything except the
provider implementation itself — see `app/db/schema.py`'s
`data_source_connections` collection docstring for why the browser never
sees them.
"""
from __future__ import annotations

import abc
from datetime import datetime

from app.parsers.base import ParsedTable


class DataSourceConnectionError(Exception):
    """Raised when credentials are invalid or the provider can't be reached — always human-readable."""


class DataSourceProvider(abc.ABC):
    key: str
    label: str

    @abc.abstractmethod
    async def test_connection(self, credentials: dict) -> str:
        """
        Verifies the credentials actually work by making one real, cheap
        call to the provider. Returns a human-readable display name for the
        connection (e.g. the shop's name) on success. Raises
        DataSourceConnectionError with a clear reason on failure.
        """

    @abc.abstractmethod
    async def fetch_orders(self, credentials: dict, since: datetime | None = None) -> ParsedTable:
        """
        Pulls recent order/transaction records and returns them as a
        ParsedTable shaped like the "orders" CSV template (order_id,
        customer_id, status, total_amount, order_date, currency, and
        product_id/unit_price/quantity/discount_amount where the source
        data supports it) — see individual providers for exactly which
        optional columns they fill in and why.
        """
