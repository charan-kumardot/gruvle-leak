"""
Demo Mode API (spec section 64) — the only endpoints in this pass that do
not require Appwrite to be configured or a real file to be uploaded. Runs
the real detector engine against a synthetic business so the frontend has
something genuine (not hand-typed fake JSON) to render. Multiple industry
profiles exist (see app/demo/demo_data.py) so a visitor can pick something
close to their own business, not just one fixed retailer.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Response

from app.demo.demo_data import DEFAULT_INDUSTRY, build_demo_context, get_profile, list_industries
from app.detectors.registry import run_all_detectors
from app.reports.builder import build_report_summary
from app.reports.exporters import to_csv, to_json, to_markdown, to_pdf
from app.schemas.domain import DetectorStatus
from app.scoring.priority import score_detector_results

router = APIRouter()

_DEMO_SCAN_DATE = date(2026, 8, 30)


def _run_demo_scan(industry: str):
    profile = get_profile(industry)
    ctx = build_demo_context(industry)
    results = score_detector_results(run_all_detectors(ctx))
    total_records = sum(r.records_evaluated for r in results if r.status == DetectorStatus.RAN)
    return build_report_summary(
        scan_id=ctx.scan_id, business_id=ctx.business_id, business_name=profile.business_name,
        scan_date=_DEMO_SCAN_DATE, records_analyzed=total_records,
        detector_results=results, data_quality_score=91, is_demo=True,
    )


@router.get("/industries")
def get_demo_industries():
    """The available synthetic business profiles a visitor can pick between."""
    return {"industries": list_industries(), "default": DEFAULT_INDUSTRY}


@router.get("/scan")
def get_demo_scan(industry: str = DEFAULT_INDUSTRY):
    """Full report summary (findings, evidence, calculations) for a synthetic demo business."""
    summary = _run_demo_scan(industry)
    return summary.model_dump(mode="json")


@router.get("/scan/report")
def get_demo_report(industry: str = DEFAULT_INDUSTRY, format: Literal["json", "csv", "markdown", "pdf"] = "json"):
    summary = _run_demo_scan(industry)
    if format == "json":
        return Response(content=to_json(summary), media_type="application/json")
    if format == "csv":
        return Response(content=to_csv(summary), media_type="text/csv",
                         headers={"Content-Disposition": f"attachment; filename=demo-{industry}-report.csv"})
    if format == "markdown":
        return Response(content=to_markdown(summary), media_type="text/markdown")
    if format == "pdf":
        return Response(content=to_pdf(summary), media_type="application/pdf",
                         headers={"Content-Disposition": f"attachment; filename=demo-{industry}-report.pdf"})
    raise HTTPException(status_code=400, detail="Unsupported format")
