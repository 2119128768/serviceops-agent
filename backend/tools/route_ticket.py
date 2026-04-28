from __future__ import annotations

from sqlalchemy.orm import Session

from backend.database.models import Ticket


def route_ticket(db: Session, ticket_id: str, team: str) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        return {"routed": False, "reason": "ticket_not_found", "ticket_id": ticket_id}
    ticket.suggested_team = team
    db.flush()
    return {"routed": True, "ticket_id": ticket_id, "team": team}
