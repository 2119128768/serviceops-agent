from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    subject: str = Field(default="未命名工单", max_length=300)
    body: str
    customer_id: str | None = None


class TicketRead(BaseModel):
    ticket_id: str
    subject: str
    body: str
    customer_id: str | None
    status: str
    intent: str | None
    product: str | None
    priority: str | None
    suggested_team: str | None
    risk_level: str | None
    missing_info: list[str]
    final_summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketRunResponse(BaseModel):
    ticket: TicketRead
    result: dict[str, Any]


class ApprovalDecision(BaseModel):
    approval_id: str
    decision: str = Field(pattern="^(approved|rejected|modified)$")
    comment: str | None = None
    modified_payload: dict[str, Any] | None = None


class RagSearchResponse(BaseModel):
    query: str
    chunks: list[dict[str, Any]]
