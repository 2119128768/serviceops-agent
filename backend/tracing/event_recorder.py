from __future__ import annotations

from sqlalchemy.orm import Session

from backend.database.models import TicketEvent


def record_event(db: Session, ticket_id: str, event_type: str, payload: dict) -> TicketEvent:
    event = TicketEvent(ticket_id=ticket_id, event_type=event_type, payload=payload)
    db.add(event)
    db.flush()
    return event
