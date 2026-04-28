from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.tracing.event_recorder import record_event


def check_missing_info(db: Session, state: AgentState) -> AgentState:
    blocking = False
    intent = state.router_output.get("intent")
    missing = set(state.missing_info)

    if intent == "api_quota_error" and "request_id" not in state.identifiers and "account_id" in missing:
        blocking = True
    if intent == "deployment_failure" and "deployment_id" in missing:
        blocking = True

    payload = {
        "missing_info": state.missing_info,
        "blocking": blocking,
        "follow_up": _follow_up_message(state.missing_info) if state.missing_info else "",
    }
    state.router_output["has_blocking_missing_info"] = blocking
    record_event(db, state.ticket_id, "missing_info_checked", payload)
    return state


def _follow_up_message(missing_info: list[str]) -> str:
    labels = {
        "account_id": "账号 ID",
        "order_id": "订单号",
        "request_id": "请求 ID",
        "project_id": "项目 ID",
        "deployment_id": "部署 ID",
    }
    readable = "、".join(labels.get(item, item) for item in missing_info)
    return f"请补充 {readable}，以便继续排查。"
