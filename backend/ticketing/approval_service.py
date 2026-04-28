from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.database.models import ApprovalRequest, Ticket
from backend.database.schemas import ApprovalDecision
from backend.tracing.event_recorder import record_event


def decide_approval(db: Session, decision: ApprovalDecision) -> ApprovalRequest:
    approval = db.get(ApprovalRequest, decision.approval_id)
    if not approval:
        raise ValueError(f"Approval not found: {decision.approval_id}")

    approval.status = decision.decision
    approval.decided_at = datetime.now(UTC).replace(tzinfo=None)
    if decision.modified_payload:
        approval.payload = {**approval.payload, "modified_payload": decision.modified_payload}

    ticket = db.get(Ticket, approval.ticket_id)
    if ticket:
        if decision.decision == "approved":
            ticket.status = "APPROVED_FOR_ACTION"
        elif decision.decision == "rejected":
            ticket.status = "APPROVAL_REJECTED"
        else:
            ticket.status = "APPROVAL_MODIFIED"

    record_event(
        db,
        approval.ticket_id,
        "approval_decided",
        {
            "approval_id": approval.approval_id,
            "decision": decision.decision,
            "comment": decision.comment,
            "modified_payload": decision.modified_payload,
        },
    )
    db.commit()
    db.refresh(approval)
    return approval
