from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database.models import ApprovalRequest, Ticket, ToolCall
from backend.database.session import get_db

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary")
def metrics_summary(db: Session = Depends(get_db)):
    tickets = db.query(Ticket).all()
    status_counts = Counter(ticket.status for ticket in tickets)
    intent_counts = Counter(ticket.intent or "unclassified" for ticket in tickets)
    tool_count = db.query(func.count(ToolCall.id)).scalar() or 0
    approval_count = db.query(func.count(ApprovalRequest.approval_id)).scalar() or 0
    avg_latency = db.query(func.avg(ToolCall.latency_ms)).scalar()

    return {
        "ticket_count": len(tickets),
        "status_counts": dict(status_counts),
        "intent_counts": dict(intent_counts),
        "tool_call_count": tool_count,
        "approval_count": approval_count,
        "avg_tool_latency_ms": round(float(avg_latency or 0), 2),
    }
