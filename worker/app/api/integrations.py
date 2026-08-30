from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import require_internal_token
from app.db.connections_repository import create_connection, delete_connection, list_connections
from app.integrations.base import DataSourceConnectionError
from app.integrations.registry import get_provider, list_providers
from app.jobs.integration_sync import sync_connection
from app.jobs.scan_pipeline import ScanPipelineError

router = APIRouter(dependencies=[Depends(require_internal_token)])


@router.get("/providers")
def get_providers():
    """Every integration the product plans to support, and which ones actually work today."""
    return {"providers": list_providers()}


class ConnectRequest(BaseModel):
    business_id: str
    team_id: str
    user_id: str
    provider: str
    credentials: dict


@router.post("/connections")
async def create_integration_connection(body: ConnectRequest):
    try:
        provider = get_provider(body.provider)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{body.provider}'.")

    try:
        display_name = await provider.test_connection(body.credentials)
    except DataSourceConnectionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))

    connection = create_connection(
        business_id=body.business_id, team_id=body.team_id, user_id=body.user_id,
        provider=body.provider, display_name=display_name, credentials=body.credentials,
    )
    return connection


@router.get("/connections")
def get_integration_connections(business_id: str, team_id: str):
    return {"connections": list_connections(team_id, business_id)}


@router.delete("/connections/{connection_id}")
def remove_integration_connection(connection_id: str, team_id: str):
    ok = delete_connection(team_id, connection_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Connection not found.")
    return {"deleted": True}


class SyncRequest(BaseModel):
    business_id: str
    team_id: str


@router.post("/connections/{connection_id}/sync")
async def sync_integration_connection(connection_id: str, body: SyncRequest):
    try:
        result = await sync_connection(business_id=body.business_id, team_id=body.team_id, connection_id=connection_id)
    except ScanPipelineError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result
