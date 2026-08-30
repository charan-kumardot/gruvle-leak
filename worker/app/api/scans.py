from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.api.deps import require_internal_token
from app.db.finding_repository import load_finding, update_finding_status
from app.db.repositories import get_business_scoped
from app.jobs.scan_pipeline import ScanPipelineError, load_report_summary, run_scan
from app.reports.exporters import to_csv, to_json, to_markdown, to_pdf
from app.schemas.domain import FindingStatus

router = APIRouter(dependencies=[Depends(require_internal_token)])


class CreateScanRequest(BaseModel):
    business_id: str
    team_id: str
    created_by_user_id: str
    dataset_ids: list[str]
    currency: str = "INR"


@router.post("")
async def create_scan(body: CreateScanRequest):
    try:
        summary = await run_scan(
            business_id=body.business_id, team_id=body.team_id, created_by_user_id=body.created_by_user_id,
            dataset_ids=body.dataset_ids, default_currency=body.currency,
        )
    except ScanPipelineError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return summary.model_dump(mode="json")


@router.get("/{scan_id}")
def get_scan(scan_id: str, team_id: str):
    doc = get_business_scoped("scans", scan_id, team_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return {
        "id": doc["$id"],
        "business_id": doc.get("business_id"),
        "stage": doc.get("stage"),
        "progress_percent": doc.get("progress_percent", 0),
        "progress_detail": doc.get("progress_detail", ""),
        "records_analyzed": doc.get("records_analyzed", 0),
        "data_quality_score": doc.get("data_quality_score"),
        "total_potential_leakage": doc.get("total_potential_leakage", 0),
        "total_high_confidence_leakage": doc.get("total_high_confidence_leakage", 0),
        "finding_count": doc.get("finding_count", 0),
        "currency": doc.get("currency", "INR"),
        "error_message": doc.get("error_message"),
        "created_at": doc.get("$createdAt"),
    }


@router.get("/{scan_id}/findings")
def get_scan_findings(scan_id: str, team_id: str):
    summary = load_report_summary(team_id, scan_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return [f.model_dump(mode="json") for f in summary.all_findings]


@router.get("/{scan_id}/report")
def get_scan_report(scan_id: str, team_id: str, format: Literal["json", "csv", "markdown", "pdf"] = "json"):
    summary = load_report_summary(team_id, scan_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    if format == "json":
        return Response(content=to_json(summary), media_type="application/json")
    if format == "csv":
        return Response(content=to_csv(summary), media_type="text/csv",
                         headers={"Content-Disposition": f"attachment; filename=scan-{scan_id}-report.csv"})
    if format == "markdown":
        return Response(content=to_markdown(summary), media_type="text/markdown")
    return Response(content=to_pdf(summary), media_type="application/pdf",
                     headers={"Content-Disposition": f"attachment; filename=scan-{scan_id}-report.pdf"})


class UpdateFindingStatusRequest(BaseModel):
    team_id: str
    status: Literal["NEW", "REVIEWING", "CONFIRMED", "DISMISSED", "RESOLVED"]
    note: Optional[str] = None


finding_router = APIRouter(dependencies=[Depends(require_internal_token)])


@finding_router.get("/{finding_id}")
def get_finding(finding_id: str, team_id: str):
    finding = load_finding(team_id, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return finding.model_dump(mode="json")


@finding_router.post("/{finding_id}/status")
def set_finding_status(finding_id: str, body: UpdateFindingStatusRequest):
    finding = update_finding_status(body.team_id, finding_id, FindingStatus(body.status), body.note)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return finding.model_dump(mode="json")
