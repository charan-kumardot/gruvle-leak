from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_internal_token
from app.jobs.account_deletion import delete_business_and_account

router = APIRouter(dependencies=[Depends(require_internal_token)])


class DeleteAccountRequest(BaseModel):
    business_id: str
    team_id: str
    user_id: str


@router.post("/delete")
def delete_account(body: DeleteAccountRequest):
    """
    Irreversibly deletes a business's data and the requesting user's
    account. The caller (web/src/app/api/account/delete/route.ts) verifies
    `user_id` against the requester's own JWT before ever reaching here —
    this endpoint trusts the internal token the same way every other worker
    route does, but the identity check that makes this safe to expose at
    all happens one layer up.
    """
    return delete_business_and_account(business_id=body.business_id, team_id=body.team_id, user_id=body.user_id)
