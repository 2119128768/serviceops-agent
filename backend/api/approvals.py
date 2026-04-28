from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.models import ApprovalRequest
from backend.database.schemas import ApprovalDecision
from backend.database.session import get_db
from backend.ticketing.approval_service import decide_approval

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
def list_approvals(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    if status:
        query = query.filter(ApprovalRequest.status == status)
    approvals = query.limit(50).all()
    return {
        "approvals": [
            {
                "approval_id": item.approval_id,
                "ticket_id": item.ticket_id,
                "action": item.action,
                "risk_reason": item.risk_reason,
                "status": item.status,
                "payload": item.payload,
                "created_at": item.created_at.isoformat(),
                "decided_at": item.decided_at.isoformat() if item.decided_at else None,
            }
            for item in approvals
        ]
    }


@router.post("/{approval_id}/decide")
def decide_approval_endpoint(
    approval_id: str, payload: ApprovalDecision, db: Session = Depends(get_db)
):
    if approval_id != payload.approval_id:
        raise HTTPException(status_code=400, detail="approval_id_mismatch")
    try:
        approval = decide_approval(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "approval_id": approval.approval_id,
        "ticket_id": approval.ticket_id,
        "status": approval.status,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }
