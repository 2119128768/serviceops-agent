from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.database.models import Ticket
from backend.tools import ToolRegistry
from backend.tracing.event_recorder import record_event


def call_tools(db: Session, state: AgentState, registry: ToolRegistry) -> AgentState:
    calls: list[tuple[str, dict]] = []
    identifiers = dict(state.identifiers)

    if "request_id" in identifiers:
        result = registry.run(
            db, state.ticket_id, "check_api_status", {"request_id": identifiers["request_id"]}
        )
        state.tool_results.append(
            {"tool_name": "check_api_status", "arguments": {"request_id": identifiers["request_id"]}, "result": result}
        )
        if result.get("found") and result.get("account_id"):
            identifiers.setdefault("account_id", result["account_id"])
            state.identifiers.setdefault("account_id", result["account_id"])

    if "deployment_id" in identifiers:
        calls.append(("get_deployment_status", {"deployment_id": identifiers["deployment_id"]}))

    if "account_id" in identifiers:
        calls.append(("get_customer_profile", {"account_id": identifiers["account_id"]}))

    if "order_id" in identifiers:
        calls.append(("query_order_status", {"order_id": identifiers["order_id"]}))
    elif state.router_output.get("intent") in {"api_quota_error", "billing_request"} and "account_id" in identifiers:
        calls.append(("query_order_status", {"account_id": identifiers["account_id"]}))

    if state.router_output.get("priority"):
        calls.append(("get_sla_policy", {"priority": state.router_output["priority"]}))

    if state.router_output.get("suggested_team"):
        calls.append(
            (
                "route_ticket",
                {"ticket_id": state.ticket_id, "team": state.router_output["suggested_team"]},
            )
        )

    for tool_name, arguments in calls:
        result = registry.run(db, state.ticket_id, tool_name, arguments)
        state.tool_results.append({"tool_name": tool_name, "arguments": arguments, "result": result})

    state.missing_info = [item for item in state.missing_info if item not in state.identifiers]
    state.router_output["missing_info"] = state.missing_info
    ticket = db.get(Ticket, state.ticket_id)
    if ticket:
        ticket.missing_info = state.missing_info

    record_event(
        db,
        state.ticket_id,
        "tools_called",
        {
            "tool_calls": [
                {
                    "tool_name": item["tool_name"],
                    "arguments": item["arguments"],
                    "success": "error" not in item["result"],
                }
                for item in state.tool_results
            ]
        },
    )
    return state
