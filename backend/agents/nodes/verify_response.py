from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.llm.verifier_model import LoraVerifierModel, VerifierModel
from backend.tracing.event_recorder import record_event


def verify_response(db: Session, state: AgentState, verifier: VerifierModel | LoraVerifierModel) -> AgentState:
    state.verifier_output = verifier.verify(
        ticket_text=state.text,
        draft_reply=state.draft_reply,
        evidence_chunks=state.rag_chunks,
        tool_results=state.tool_results,
        router_output=state.router_output,
        plan=state.plan,
    )
    record_event(db, state.ticket_id, "response_verified", state.verifier_output)
    return state
