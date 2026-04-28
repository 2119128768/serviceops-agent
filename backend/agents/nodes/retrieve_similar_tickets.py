from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.database.models import Ticket
from backend.rag.tokenizer import tokenize
from backend.tracing.event_recorder import record_event


def retrieve_similar_tickets(db: Session, state: AgentState, top_k: int = 3) -> AgentState:
    query_tokens = set(tokenize(state.text))
    candidates = (
        db.query(Ticket)
        .filter(Ticket.ticket_id != state.ticket_id)
        .filter(Ticket.status.in_(["RESOLVED", "ESCALATED", "WAITING_HUMAN_APPROVAL"]))
        .all()
    )
    scored: list[tuple[Ticket, float]] = []
    for ticket in candidates:
        tokens = set(tokenize(f"{ticket.subject}\n{ticket.body}\n{ticket.intent or ''}"))
        if not tokens:
            continue
        score = len(query_tokens & tokens) / len(query_tokens | tokens)
        if ticket.intent and ticket.intent == state.router_output.get("intent"):
            score += 0.25
        if score > 0:
            scored.append((ticket, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    state.similar_tickets = [
        {
            "ticket_id": ticket.ticket_id,
            "subject": ticket.subject,
            "intent": ticket.intent,
            "priority": ticket.priority,
            "score": round(score, 4),
            "resolution": ticket.final_summary.get("resolution") if ticket.final_summary else None,
        }
        for ticket, score in scored[:top_k]
    ]
    record_event(db, state.ticket_id, "similar_tickets_retrieved", {"tickets": state.similar_tickets})
    return state
