"""
Pulls orders from a connected data source (Shopify today) and feeds them
into the exact same ingestion pipeline a manual file upload uses — see
`app/jobs/scan_pipeline.py::ingest_table`'s docstring for why the fetched
rows are serialized to real CSV bytes first rather than special-cased.
"""
from __future__ import annotations

import csv
import io

from app.db.connections_repository import get_connection_with_credentials, mark_sync_error, mark_sync_success
from app.integrations.base import DataSourceConnectionError
from app.integrations.registry import get_provider
from app.jobs.scan_pipeline import ScanPipelineError, ingest_table
from app.parsers.base import ParsedTable


def _table_to_csv_bytes(table: ParsedTable) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=table.columns, extrasaction="ignore")
    writer.writeheader()
    for row in table.rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


async def sync_connection(*, business_id: str, team_id: str, connection_id: str) -> dict:
    connection = get_connection_with_credentials(team_id, connection_id)
    if connection is None:
        raise ScanPipelineError("This connection was not found for your business.")

    provider = get_provider(connection["provider"])

    try:
        table = await provider.fetch_orders(connection["credentials"])
    except DataSourceConnectionError as e:
        mark_sync_error(team_id, connection_id, str(e))
        raise ScanPipelineError(str(e)) from e

    if not table.rows:
        mark_sync_success(team_id, connection_id)
        raise ScanPipelineError(
            f"Connected to {connection['display_name']} successfully, but no orders were found to import."
        )

    csv_bytes = _table_to_csv_bytes(table)
    filename = f"{connection['provider']}-orders-sync.csv"

    result = await ingest_table(
        business_id=business_id, team_id=team_id, table=table, filename=filename,
        content_for_storage=csv_bytes, content_type="text/csv",
        source=connection["provider"], source_connection_id=connection_id,
    )

    mark_sync_success(team_id, connection_id)
    return result
