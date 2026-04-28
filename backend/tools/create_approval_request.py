from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from backend.database.models import ApprovalRequest


def create_approval_request(
    db: Session, ticket_id: str, action: str, risk_reason: str, payload: dict
) -> dict:
    approval = ApprovalRequest(
        approval_id=f"apr_{uuid4().hex[:12]}",
        ticket_id=ticket_id,
        action=action,
        risk_reason=risk_reason,
        payload=payload,
    )
    db.add(approval)
    db.flush()
    return {
        "approval_id": approval.approval_id,
        "ticket_id": ticket_id,
        "action": action,
        "risk_reason": risk_reason,
        "status": approval.status,
    }
