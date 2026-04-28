from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agents import ServiceOpsAgent
from backend.database.models import Ticket, TicketEvent
from backend.database.schemas import TicketCreate, TicketRead, TicketRunResponse
from backend.database.session import get_db
from backend.ticketing.ticket_service import create_ticket, list_tickets

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("/create", response_model=TicketRead)
def create_ticket_endpoint(payload: TicketCreate, db: Session = Depends(get_db)):
    return create_ticket(db, payload)


@router.get("", response_model=list[TicketRead])
def list_tickets_endpoint(limit: int = 50, db: Session = Depends(get_db)):
    return list_tickets(db, limit=limit)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket_endpoint(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket_not_found")
    return ticket


@router.post("/{ticket_id}/run-agent", response_model=TicketRunResponse)
def run_agent_endpoint(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket_not_found")
    try:
        result = ServiceOpsAgent().run(db, ticket_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.refresh(ticket)
    return {"ticket": ticket, "result": result}


@router.get("/{ticket_id}/trace")
def get_trace_endpoint(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket_not_found")
    events = (
        db.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.created_at.asc(), TicketEvent.id.asc())
        .all()
    )
    return {
        "ticket_id": ticket_id,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }
