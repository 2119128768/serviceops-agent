from __future__ import annotations

import os
from abc import ABC, abstractmethod


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        raise NotImplementedError


class NoopReranker(Reranker):
    def rerank(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        return chunks[:top_k]


class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Install it with "
                "`pip install -e '.[rag]'` or set RERANKER_BACKEND=none."
            ) from exc

        try:
            self.model = CrossEncoder(model_name)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load reranker model {model_name!r}. "
                "Check network/cache access or set RERANKER_BACKEND=none."
            ) from exc

    def rerank(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        pairs = [(query, chunk["content"]) for chunk in chunks]
        scores = self.model.predict(pairs)
        scored = []
        for chunk, score in zip(chunks, scores):
            item = dict(chunk)
            item["rerank_score"] = float(score)
            scored.append(item)
        scored.sort(key=lambda item: item["rerank_score"], reverse=True)
        return scored[:top_k]


def make_reranker(backend: str | None = None, model_name: str | None = None) -> Reranker:
    selected = (backend or os.getenv("RERANKER_BACKEND", "none")).lower()
    if selected in {"none", "noop"}:
        return NoopReranker()
    if selected == "cross_encoder":
        return CrossEncoderReranker(model_name or os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base"))
    raise ValueError(f"Unsupported RERANKER_BACKEND={selected!r}")
