from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.database.models import KnowledgeUpdate
from backend.tracing.event_recorder import record_event


def update_knowledge(db: Session, state: AgentState) -> AgentState:
    if state.router_output.get("intent") not in {"api_quota_error", "deployment_failure", "rag_retrieval_issue"}:
        return state

    title = f"{state.router_output.get('intent')} 处理建议补充"
    proposed = (
        f"来源工单：{state.ticket_id}\n"
        f"分类：{state.router_output.get('intent')}\n"
        f"建议补充：{'; '.join(state.plan.get('steps', [])[:3])}\n"
        "注意：该建议需要知识库负责人审批后才能写入正式文档。"
    )
    update_id = f"kbu_{uuid4().hex[:12]}"
    db.add(
        KnowledgeUpdate(
            update_id=update_id,
            ticket_id=state.ticket_id,
            title=title,
            proposed_content=proposed,
            evidence={
                "rag_chunk_ids": [chunk["chunk_id"] for chunk in state.rag_chunks],
                "tool_names": [item["tool_name"] for item in state.tool_results],
            },
        )
    )
    state.knowledge_update = {
        "update_id": update_id,
        "title": title,
        "status": "proposed",
        "requires_approval": True,
    }
    record_event(db, state.ticket_id, "knowledge_update_proposed", state.knowledge_update)
    return state
