from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from backend.database.models import Ticket
from backend.database.schemas import TicketCreate
from backend.tracing.event_recorder import record_event


def create_ticket(db: Session, payload: TicketCreate) -> Ticket:
    ticket_id = f"T{uuid4().hex[:10].upper()}"
    ticket = Ticket(
        ticket_id=ticket_id,
        subject=payload.subject,
        body=payload.body,
        customer_id=payload.customer_id,
        status="CREATED",
        missing_info=[],
        final_summary={},
    )
    db.add(ticket)
    db.flush()
    record_event(
        db,
        ticket_id,
        "ticket_created",
        {"subject": payload.subject, "customer_id": payload.customer_id},
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets(db: Session, limit: int = 50) -> list[Ticket]:
    return db.query(Ticket).order_by(Ticket.created_at.desc()).limit(limit).all()
