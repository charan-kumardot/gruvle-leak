"""
End-to-end orchestration: upload -> parse -> profile -> map (upload time),
then dataset(s) -> detect -> score -> persist -> report (scan time).

Runs synchronously within the HTTP request for both stages — acceptable for
the file sizes this MVP targets (spec: optimize for 10MB files initially).
A background job queue (spec section 55) is planned but not required for
correctness at this scale; see docs/ARCHITECTURE.md for what's deferred.

Only tabular files (CSV/XLSX/JSON) feed the detection pipeline in this pass.
A PDF with no detectable table (`parse_file` falling back to
`extract_text_blocks`) is rejected here with a clear message rather than
silently skipped — full PDF-contract-to-structured-data extraction is
`ContractLeakDetector`'s job (currently a registered stub, see
`app/detectors/stubs.py`), not this pipeline's.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal

from appwrite.id import ID
from appwrite.query import Query

from app.ai.base import AIProviderError
from app.db.client import get_databases
from app.db.finding_repository import load_scan_findings, save_scan_findings
from app.db.repositories import (
    create_business_scoped_document,
    get_business_scoped,
    list_business_scoped,
    update_business_scoped_document,
)
from app.db.schema import DATABASE_ID
from app.detectors.base import DatasetBundle, DetectionContext
from app.detectors.registry import run_all_detectors
from app.mapping.mapper import map_columns
from app.mapping.normalize import apply_mapping
from app.parsers.base import ParsedTable
from app.parsers.dispatch import parse_file
from app.parsers.validation import ValidationError
from app.profiling.profiler import profile_dataset
from app.profiling.quality_score import compute_data_quality_score
from app.reports.builder import build_report_summary
from app.reports.schemas import ReportSummary
from app.schemas.domain import (
    CanonicalField,
    ColumnMapping,
    DataMapping,
    DatasetKind,
    DatasetProfile,
    DetectorStatus,
    ScanStage,
)
from app.scoring.priority import score_detector_results, total_impact_by_type
from app.storage.factory import get_storage_provider

FILES_BUCKET = "generated_reports"  # the single shared bucket — see app/db/schema.py


class ScanPipelineError(Exception):
    """A clear, user-facing failure reason (bad upload, unmappable data, missing dataset)."""


async def process_dataset_upload(
    *, business_id: str, team_id: str, filename: str, content: bytes, declared_content_type: str
) -> dict:
    try:
        table = parse_file(content, filename, declared_content_type)
    except ValidationError as e:
        raise ScanPipelineError(str(e)) from e

    if not isinstance(table, ParsedTable):
        raise ScanPipelineError(
            "This PDF doesn't contain a detectable table of records. Gruvle can extract key details from "
            "PDF invoices/contracts in a future update — for now, please upload a CSV or Excel export instead."
        )
    if not table.rows:
        raise ScanPipelineError("This file has no data rows to analyze.")

    return await ingest_table(
        business_id=business_id, team_id=team_id, table=table, filename=filename,
        content_for_storage=content, content_type=declared_content_type, source="upload", source_connection_id=None,
    )


async def ingest_table(
    *, business_id: str, team_id: str, table: ParsedTable, filename: str,
    content_for_storage: bytes, content_type: str, source: str, source_connection_id: str | None,
) -> dict:
    """
    Shared by both `process_dataset_upload` (a human uploads a file) and
    `app/jobs/integration_sync.py` (a connected data source like Shopify is
    synced) — profile, map, store, persist. A synced connection's rows are
    serialized to CSV bytes by the caller before reaching here specifically
    so this function, and the storage/re-parse round-trip `run_scan` later
    does, never need to know the data didn't originate from a literal file.
    """
    dataset_id = ID.unique()
    profile: DatasetProfile = profile_dataset(dataset_id, table)

    try:
        mapping: DataMapping = await map_columns(dataset_id, profile, table.rows[:5])
    except AIProviderError as e:
        raise ScanPipelineError(f"Could not map your columns: {e}") from e

    quality = compute_data_quality_score(profile, mapping)

    storage = get_storage_provider()
    _, ext = os.path.splitext(filename.lower())
    storage_file_id = await storage.upload(
        bucket=FILES_BUCKET, file_id=f"upload-{dataset_id}", filename=f"upload/{dataset_id}/{filename}",
        content=content_for_storage, content_type=content_type,
    )

    create_business_scoped_document(
        "datasets", business_id, team_id,
        data={
            "kind": profile.inferred_kind.value,
            "original_filename": filename,
            "file_type": ext.lstrip("."),
            "file_size_bytes": len(content_for_storage),
            "storage_file_id": storage_file_id,
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "processing_status": "profiled",
            "source": source,
            "source_connection_id": source_connection_id,
        },
        document_id=dataset_id,
    )

    for col in profile.columns:
        create_business_scoped_document(
            "dataset_columns", business_id, team_id,
            data={
                "dataset_id": dataset_id,
                "raw_name": col.raw_name,
                "inferred_type": col.inferred_type,
                "non_null_count": col.non_null_count,
                "null_count": col.null_count,
                "distinct_count": col.distinct_count,
            },
        )

    for m in mapping.mappings:
        create_business_scoped_document(
            "data_mappings", business_id, team_id,
            data={
                "dataset_id": dataset_id,
                "raw_name": m.raw_name,
                "canonical_field": m.canonical_field.value if m.canonical_field else None,
                "confidence": m.confidence,
                "source": m.source,
                "reason": m.reason,
            },
        )

    return {
        "dataset_id": dataset_id,
        "kind": profile.inferred_kind.value,
        "kind_confidence": profile.inferred_kind_confidence,
        "row_count": profile.row_count,
        "column_count": profile.column_count,
        "warnings": profile.warnings + table.warnings,
        "mapping": [
            {"raw_name": m.raw_name, "canonical_field": m.canonical_field.value if m.canonical_field else None,
             "confidence": m.confidence, "source": m.source, "reason": m.reason}
            for m in mapping.mappings
        ],
        "unmapped_required_fields": [f.value for f in mapping.unmapped_required_fields],
        "data_quality_score": quality.overall_score,
        "data_quality_explanations": quality.explanations,
    }


def list_datasets(team_id: str, business_id: str) -> list[dict]:
    docs = list_business_scoped("datasets", team_id, queries=[Query.equal("business_id", business_id)])
    return [
        {
            "id": d["$id"],
            "kind": d.get("kind"),
            "original_filename": d.get("original_filename"),
            "file_type": d.get("file_type"),
            "row_count": d.get("row_count", 0),
            "column_count": d.get("column_count", 0),
            "source": d.get("source", "upload"),
            "processing_status": d.get("processing_status"),
            "created_at": d.get("$createdAt"),
        }
        for d in docs
    ]


async def delete_dataset(team_id: str, dataset_id: str) -> bool:
    """
    Deletes a dataset, its column profile, and its column mapping. Past
    scans/findings that were computed from it are left alone (spec:
    deleting a dataset is its own action — it doesn't retroactively
    invalidate a report already generated from it).
    """
    dataset_doc = get_business_scoped("datasets", dataset_id, team_id)
    if dataset_doc is None:
        return False

    for coll in ("dataset_columns", "data_mappings"):
        for doc in list_business_scoped(coll, team_id, queries=[Query.equal("dataset_id", dataset_id)]):
            get_databases().delete_document(DATABASE_ID, coll, doc["$id"])

    storage_file_id = dataset_doc.get("storage_file_id")
    if storage_file_id:
        try:
            await get_storage_provider().delete(bucket=FILES_BUCKET, file_id=storage_file_id)
        except Exception:  # noqa: BLE001 — storage cleanup is best-effort, must not block the delete
            pass

    get_databases().delete_document(DATABASE_ID, "datasets", dataset_id)
    return True


def _load_mapping(team_id: str, dataset_id: str) -> DataMapping:
    docs = list_business_scoped("data_mappings", team_id, queries=[Query.equal("dataset_id", dataset_id)])
    mappings = [
        ColumnMapping(
            raw_name=d["raw_name"],
            canonical_field=CanonicalField(d["canonical_field"]) if d.get("canonical_field") else None,
            confidence=d.get("confidence", 0.0),
            source=d.get("source", "heuristic"),
            reason=d.get("reason", ""),
        )
        for d in docs
    ]
    return DataMapping(dataset_id=dataset_id, mappings=mappings, unmapped_required_fields=[])


async def run_scan(*, business_id: str, team_id: str, created_by_user_id: str, dataset_ids: list[str],
                    default_currency: str = "INR") -> ReportSummary:
    if not dataset_ids:
        raise ScanPipelineError("Select at least one dataset to scan.")

    scan_id = ID.unique()
    create_business_scoped_document(
        "scans", business_id, team_id,
        data={"created_by_user_id": created_by_user_id, "stage": ScanStage.DETECTING.value,
              "progress_percent": 10, "progress_detail": "Loading datasets…", "currency": default_currency},
        document_id=scan_id,
    )

    try:
        storage = get_storage_provider()
        bundles: list[DatasetBundle] = []
        business_name = "Your business"
        business_doc = get_business_scoped("businesses", business_id, team_id)
        if business_doc:
            business_name = business_doc.get("name", business_name)
            default_currency = business_doc.get("currency", default_currency)

        for dataset_id in dataset_ids:
            ds_doc = get_business_scoped("datasets", dataset_id, team_id)
            if ds_doc is None:
                raise ScanPipelineError(f"Dataset {dataset_id} was not found for this business.")

            content = await storage.download(bucket=FILES_BUCKET, file_id=ds_doc["storage_file_id"])
            table = parse_file(content, ds_doc["original_filename"], f"application/{ds_doc['file_type']}")
            if not isinstance(table, ParsedTable):
                continue  # shouldn't happen — upload already rejected non-tabular files

            mapping = _load_mapping(team_id, dataset_id)
            records = apply_mapping(dataset_id, table, mapping)
            bundles.append(DatasetBundle(dataset_id, DatasetKind(ds_doc["kind"]), records))

        update_business_scoped_document("scans", scan_id, team_id,
                                         {"progress_percent": 40, "progress_detail": "Running leak detectors…"})

        ctx = DetectionContext(scan_id=scan_id, business_id=business_id, default_currency=default_currency,
                                datasets=bundles)
        results = score_detector_results(run_all_detectors(ctx))

        update_business_scoped_document("scans", scan_id, team_id,
                                         {"progress_percent": 80, "progress_detail": "Saving findings…"})
        save_scan_findings(business_id, team_id, results)

        total_records = sum(r.records_evaluated for r in results if r.status == DetectorStatus.RAN)
        totals = total_impact_by_type([f for r in results for f in r.findings])
        total_potential = sum((amt for by_ccy in totals.get("POTENTIAL_LEAKAGE", {}).values() for amt in [by_ccy]), Decimal("0"))
        all_findings = [f for r in results for f in r.findings]
        high_conf_total = sum((f.financial_impact.amount for f in all_findings if f.confidence.value == "HIGH"), Decimal("0"))

        update_business_scoped_document(
            "scans", scan_id, team_id,
            {
                "stage": ScanStage.COMPLETED.value, "progress_percent": 100, "progress_detail": "Done.",
                "records_analyzed": total_records,
                "detectors_run": [r.detector_name for r in results if r.status == DetectorStatus.RAN],
                "total_potential_leakage": float(total_potential),
                "total_high_confidence_leakage": float(high_conf_total),
                "finding_count": len(all_findings),
                "currency": default_currency,
            },
        )

        return build_report_summary(
            scan_id=scan_id, business_id=business_id, business_name=business_name,
            scan_date=date.today(), records_analyzed=total_records,
            detector_results=results, data_quality_score=None,
        )
    except Exception as e:
        update_business_scoped_document(
            "scans", scan_id, team_id,
            {"stage": ScanStage.FAILED.value, "error_message": str(e)[:1000]},
        )
        if isinstance(e, ScanPipelineError):
            raise
        raise ScanPipelineError(f"The scan could not be completed: {e}") from e


def load_report_summary(team_id: str, scan_id: str) -> ReportSummary | None:
    scan_doc = get_business_scoped("scans", scan_id, team_id)
    if scan_doc is None:
        return None
    findings = load_scan_findings(team_id, scan_id)

    ranked = sorted(findings, key=lambda f: -f.priority_score)
    from app.reports.schemas import ImpactTotal

    totals = total_impact_by_type(findings)
    impact_totals = [
        ImpactTotal(impact_type=impact_type, currency=currency, amount=amount)
        for impact_type, by_currency in totals.items()
        for currency, amount in by_currency.items()
    ]

    business_doc = None
    business_id = scan_doc.get("business_id")
    if business_id:
        business_doc = get_business_scoped("businesses", business_id, team_id)

    created_at = scan_doc.get("$createdAt")
    scan_date = (
        datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
        if created_at else date.today()
    )

    return ReportSummary(
        scan_id=scan_id,
        business_id=scan_doc.get("business_id", ""),
        business_name=(business_doc or {}).get("name", "Your business"),
        scan_date=scan_date,
        records_analyzed=scan_doc.get("records_analyzed", 0),
        detectors_run=scan_doc.get("detectors_run") or [],
        detectors_skipped=[],
        data_quality_score=scan_doc.get("data_quality_score"),
        impact_totals=impact_totals,
        finding_count=len(findings),
        high_confidence_count=sum(1 for f in findings if f.confidence.value == "HIGH"),
        top_findings=ranked[:5],
        all_findings=ranked,
        data_limitations=[],
        is_demo=scan_doc.get("is_demo", False),
    )
