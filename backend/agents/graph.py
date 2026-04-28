from __future__ import annotations

import os
import warnings

from sqlalchemy.orm import Session

from backend.agents.nodes.call_tools import call_tools
from backend.agents.nodes.check_missing_info import check_missing_info
from backend.agents.nodes.classify_ticket import classify_ticket
from backend.agents.nodes.draft_reply import draft_reply
from backend.agents.nodes.plan_solution import plan_solution
from backend.agents.nodes.request_approval import request_approval
from backend.agents.nodes.retrieve_knowledge import retrieve_knowledge
from backend.agents.nodes.retrieve_similar_tickets import retrieve_similar_tickets
from backend.agents.nodes.update_knowledge import update_knowledge
from backend.agents.nodes.verify_response import verify_response
from backend.agents.state import AgentState
from backend.database.models import Ticket
from backend.llm.local_lora_runtime import LocalModelUnavailable, build_local_lora_runtime_from_env
from backend.llm.router_model import LoraRouterModel, RouterModel
from backend.llm.verifier_model import LoraVerifierModel, VerifierModel
from backend.rag import HybridRetriever
from backend.tools import ToolRegistry
from backend.tracing.event_recorder import record_event


class ServiceOpsAgent:
    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        tools: ToolRegistry | None = None,
        router: RouterModel | None = None,
        verifier: VerifierModel | None = None,
    ) -> None:
        self.retriever = retriever or HybridRetriever()
        self.tools = tools or ToolRegistry()
        default_router, default_verifier = _default_models_from_env()
        self.router = router or default_router
        self.verifier = verifier or default_verifier

    def run(self, db: Session, ticket_id: str) -> dict:
        ticket = db.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")

        state = AgentState.from_ticket(ticket)
        record_event(db, ticket_id, "agent_started", {"workflow": "serviceops_agent_v1"})

        state = classify_ticket(db, state, self.router)
        state = check_missing_info(db, state)
        state = retrieve_knowledge(db, state, self.retriever)
        state = retrieve_similar_tickets(db, state)
        state = call_tools(db, state, self.tools)
        state = plan_solution(db, state)
        state = draft_reply(db, state)
        state = verify_response(db, state, self.verifier)
        state = request_approval(db, state, self.tools)
        state = update_knowledge(db, state)

        ticket.final_summary = state.to_result()
        db.commit()
        return state.to_result()


def _default_models_from_env() -> tuple[RouterModel | LoraRouterModel, VerifierModel | LoraVerifierModel]:
    if os.getenv("RUN_LORA") != "1":
        return RouterModel(), VerifierModel()

    try:
        runtime = build_local_lora_runtime_from_env()
        return LoraRouterModel(runtime=runtime), LoraVerifierModel(runtime=runtime)
    except LocalModelUnavailable as exc:
        if os.getenv("ALLOW_LORA_FALLBACK") == "1":
            warnings.warn(
                f"RUN_LORA=1 but local LoRA runtime is unavailable; falling back to baseline models: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return RouterModel(), VerifierModel()
        raise RuntimeError(
            "RUN_LORA=1 but local LoRA runtime is unavailable. "
            "Run `bash scripts/check_local_model.sh` or set ALLOW_LORA_FALLBACK=1 for baseline demo fallback."
        ) from exc
