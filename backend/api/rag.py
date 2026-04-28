from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Query

from backend.database.schemas import RagSearchResponse
from backend.rag import HybridRetriever

router = APIRouter(prefix="/rag", tags=["rag"])


@lru_cache(maxsize=1)
def get_retriever() -> HybridRetriever:
    return HybridRetriever()


@router.get("/search", response_model=RagSearchResponse)
def search_rag(q: str = Query(min_length=1), top_k: int = 5, category: str | None = None):
    chunks = get_retriever().search(q, top_k=top_k, category=category)
    return {"query": q, "chunks": chunks}
