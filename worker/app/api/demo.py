"""
Demo Mode API (spec section 64) — the only endpoint in this pass that does
not require Appwrite to be configured or a real file to be uploaded. It runs
the real detector engine against the synthetic "Demo Retail Co." dataset so
the frontend has something genuine (not hand-typed fake JSON) to render
while real-scan wiring is completed.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Response

from app.demo.demo_data import DEMO_BUSINESS_ID, DEMO_BUSINESS_NAME, DEMO_SCAN_ID, build_demo_context
from app.detectors.registry import run_all_detectors
from app.reports.builder import build_report_summary
from app.reports.exporters import to_csv, to_json, to_markdown, to_pdf
from app.schemas.domain import DetectorStatus
from app.scoring.priority import score_detector_results

router = APIRouter()

_DEMO_SCAN_DATE = date(2026, 8, 30)


def _run_demo_scan():
    ctx = build_demo_context()
    results = score_detector_results(run_all_detectors(ctx))
    total_records = sum(r.records_evaluated for r in results if r.status == DetectorStatus.RAN)
    return build_report_summary(
        scan_id=DEMO_SCAN_ID, business_id=DEMO_BUSINESS_ID, business_name=DEMO_BUSINESS_NAME,
        scan_date=_DEMO_SCAN_DATE, records_analyzed=total_records,
        detector_results=results, data_quality_score=91, is_demo=True,
    )


@router.get("/scan")
def get_demo_scan():
    """Full report summary (findings, evidence, calculations) for the synthetic demo business."""
    summary = _run_demo_scan()
    return summary.model_dump(mode="json")


@router.get("/scan/report")
def get_demo_report(format: Literal["json", "csv", "markdown", "pdf"] = "json"):
    summary = _run_demo_scan()
    if format == "json":
        return Response(content=to_json(summary), media_type="application/json")
    if format == "csv":
        return Response(content=to_csv(summary), media_type="text/csv",
                         headers={"Content-Disposition": "attachment; filename=demo-scan-report.csv"})
    if format == "markdown":
        return Response(content=to_markdown(summary), media_type="text/markdown")
    if format == "pdf":
        return Response(content=to_pdf(summary), media_type="application/pdf",
                         headers={"Content-Disposition": "attachment; filename=demo-scan-report.pdf"})
    raise HTTPException(status_code=400, detail="Unsupported format")
