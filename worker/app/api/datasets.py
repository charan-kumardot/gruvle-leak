from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import require_internal_token
from app.jobs.scan_pipeline import ScanPipelineError, delete_dataset, list_datasets, process_dataset_upload

router = APIRouter(dependencies=[Depends(require_internal_token)])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    business_id: str = Form(...),
    team_id: str = Form(...),
):
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than the 50MB upload limit.")

    try:
        result = await process_dataset_upload(
            business_id=business_id, team_id=team_id, filename=file.filename or "upload",
            content=content, declared_content_type=file.content_type or "application/octet-stream",
        )
    except ScanPipelineError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return result


@router.get("")
def get_datasets(business_id: str, team_id: str):
    return {"datasets": list_datasets(team_id, business_id)}


@router.delete("/{dataset_id}")
async def remove_dataset(dataset_id: str, team_id: str):
    ok = await delete_dataset(team_id, dataset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return {"deleted": True}
