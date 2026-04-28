from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.database.models import RetrievedChunk
from backend.rag.hybrid_retriever import HybridRetriever
from backend.tracing.event_recorder import record_event


def retrieve_knowledge(db: Session, state: AgentState, retriever: HybridRetriever) -> AgentState:
    query = _build_query(state)
    chunks = retriever.search(query, top_k=5)
    state.rag_chunks = chunks

    for chunk in chunks:
        db.add(
            RetrievedChunk(
                ticket_id=state.ticket_id,
                query=query,
                doc_id=chunk["doc_id"],
                chunk_id=chunk["chunk_id"],
                title=chunk["title"],
                source_path=chunk["source_path"],
                score=chunk["score"],
                content_preview=chunk["content"][:500],
            )
        )

    record_event(
        db,
        state.ticket_id,
        "knowledge_retrieved",
        {
            "query": query,
            "chunks": [
                {
                    "doc_id": chunk["doc_id"],
                    "chunk_id": chunk["chunk_id"],
                    "title": chunk["title"],
                    "score": chunk["score"],
                }
                for chunk in chunks
            ],
        },
    )
    return state


def _build_query(state: AgentState) -> str:
    parts = [state.router_output.get("intent", ""), state.router_output.get("product", ""), state.body]
    if state.identifiers:
        parts.append(" ".join(state.identifiers.values()))
    return " ".join(part for part in parts if part)
