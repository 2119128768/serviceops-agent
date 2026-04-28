from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from sqlalchemy.orm import Session

from backend.database.models import ToolCall
from backend.tools.check_api_status import check_api_status
from backend.tools.create_approval_request import create_approval_request
from backend.tools.get_customer_profile import get_customer_profile
from backend.tools.get_deployment_status import get_deployment_status
from backend.tools.get_sla_policy import get_sla_policy
from backend.tools.query_order_status import query_order_status
from backend.tools.route_ticket import route_ticket


ToolFn = Callable[..., dict]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {
            "check_api_status": check_api_status,
            "query_order_status": query_order_status,
            "get_customer_profile": get_customer_profile,
            "get_deployment_status": get_deployment_status,
            "get_sla_policy": get_sla_policy,
            "route_ticket": route_ticket,
            "create_approval_request": create_approval_request,
        }

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

    def run(self, db: Session, ticket_id: str, tool_name: str, arguments: dict[str, Any]) -> dict:
        if tool_name not in self._tools:
            result = {"error": "unknown_tool", "tool_name": tool_name}
            self._persist(db, ticket_id, tool_name, arguments, result, False, 0)
            return result

        started = perf_counter()
        success = True
        try:
            result = self._tools[tool_name](db=db, **arguments)
        except Exception as exc:  # pragma: no cover - defensive trace path
            success = False
            result = {"error": type(exc).__name__, "message": str(exc)}
        latency_ms = int((perf_counter() - started) * 1000)
        self._persist(db, ticket_id, tool_name, arguments, result, success, latency_ms)
        return result

    def _persist(
        self,
        db: Session,
        ticket_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict,
        success: bool,
        latency_ms: int,
    ) -> None:
        db.add(
            ToolCall(
                ticket_id=ticket_id,
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=success,
                latency_ms=latency_ms,
            )
        )
        db.flush()
