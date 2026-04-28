from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.extractors import extract_identifiers
from backend.agents.state import AgentState
from backend.database.models import Ticket
from backend.llm.router_model import LoraRouterModel, RouterModel
from backend.tracing.event_recorder import record_event


def classify_ticket(db: Session, state: AgentState, router: RouterModel | LoraRouterModel) -> AgentState:
    ticket = db.get(Ticket, state.ticket_id)
    output = router.classify(state.text)
    state.identifiers = extract_identifiers(state.text)
    state.router_output = output
    state.missing_info = output.get("missing_info", [])

    if ticket:
        ticket.intent = output["intent"]
        ticket.product = output["product"]
        ticket.priority = output["priority"]
        ticket.suggested_team = output["suggested_team"]
        ticket.risk_level = "medium" if output.get("requires_human") else "low"
        ticket.missing_info = state.missing_info
        ticket.status = "CLASSIFIED"

    record_event(
        db,
        state.ticket_id,
        "classified",
        {"router_output": output, "identifiers": state.identifiers},
    )
    return state
