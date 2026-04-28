from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.database.models import Ticket


@dataclass
class AgentState:
    ticket_id: str
    subject: str
    body: str
    identifiers: dict[str, str] = field(default_factory=dict)
    router_output: dict[str, Any] = field(default_factory=dict)
    missing_info: list[str] = field(default_factory=list)
    rag_chunks: list[dict[str, Any]] = field(default_factory=list)
    similar_tickets: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] = field(default_factory=dict)
    draft_reply: str = ""
    internal_note: str = ""
    verifier_output: dict[str, Any] = field(default_factory=dict)
    approval: dict[str, Any] | None = None
    knowledge_update: dict[str, Any] | None = None
    final_status: str = "CREATED"

    @property
    def text(self) -> str:
        return f"{self.subject}\n{self.body}".strip()

    @classmethod
    def from_ticket(cls, ticket: Ticket) -> "AgentState":
        return cls(ticket_id=ticket.ticket_id, subject=ticket.subject, body=ticket.body)

    def to_result(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "classification": self.router_output,
            "identified_info": self.identifiers,
            "missing_info": self.missing_info,
            "rag_chunks": self.rag_chunks,
            "similar_tickets": self.similar_tickets,
            "tool_results": self.tool_results,
            "plan": self.plan,
            "draft_reply": self.draft_reply,
            "internal_note": self.internal_note,
            "verifier": self.verifier_output,
            "approval": self.approval,
            "knowledge_update": self.knowledge_update,
            "final_status": self.final_status,
        }
