from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.database.models import Ticket
from backend.tools import ToolRegistry
from backend.tracing.event_recorder import record_event


def request_approval(db: Session, state: AgentState, registry: ToolRegistry) -> AgentState:
    ticket = db.get(Ticket, state.ticket_id)
    requires_approval = state.verifier_output.get("requires_approval", False)
    blocking_missing = state.router_output.get("has_blocking_missing_info", False)

    if requires_approval:
        reason = _approval_reason(state)
        state.approval = registry.run(
            db,
            state.ticket_id,
            "create_approval_request",
            {
                "ticket_id": state.ticket_id,
                "action": "send_customer_reply_and_route_ticket",
                "risk_reason": reason,
                "payload": {
                    "draft_reply": state.draft_reply,
                    "internal_note": state.internal_note,
                    "verifier": state.verifier_output,
                    "tool_results": state.tool_results,
                },
            },
        )
        state.final_status = "WAITING_HUMAN_APPROVAL"
    elif blocking_missing:
        state.final_status = "WAITING_CUSTOMER"
    elif state.router_output.get("priority") in {"P0", "P1"}:
        state.final_status = "ESCALATED"
    else:
        state.final_status = "RESOLVED"

    if ticket:
        ticket.status = state.final_status
        ticket.risk_level = state.verifier_output.get("risk_level")
        ticket.final_summary = state.to_result()

    record_event(
        db,
        state.ticket_id,
        "approval_or_final_status_decided",
        {"approval": state.approval, "final_status": state.final_status},
    )
    return state


def _approval_reason(state: AgentState) -> str:
    if state.verifier_output.get("unsupported_claims"):
        return "回复草稿存在未被证据支持的表述，需要人工修改后发送。"
    if state.router_output.get("requires_human"):
        return "该工单涉及账号、订单、额度或正式客户回复，需要人工审批。"
    return "Verifier 判定存在敏感动作，需要人工审批。"
