from __future__ import annotations

import os
from pathlib import Path

from backend.rag.bm25_retriever import BM25Retriever
from backend.rag.document_loader import DocumentChunk, load_markdown_chunks
from backend.rag.embeddings import EmbeddingBackend, make_embedding_backend
from backend.rag.reranker import Reranker, make_reranker
from backend.rag.vector_retriever import VectorRetriever


class HybridRetriever:
    def __init__(
        self,
        docs_path: str | Path | None = None,
        embedding_backend: EmbeddingBackend | None = None,
        reranker: Reranker | None = None,
        retrieval_mode: str = "hybrid",
    ) -> None:
        self.docs_path = Path(docs_path or os.getenv("KB_DOCS_PATH", "data/kb_docs"))
        self.chunks = load_markdown_chunks(self.docs_path)
        self.embedding_backend = embedding_backend or make_embedding_backend()
        self.reranker = reranker or make_reranker()
        self.retrieval_mode = retrieval_mode
        self.bm25 = BM25Retriever(self.chunks)
        self.vector = VectorRetriever(self.chunks, embedding_backend=self.embedding_backend)

    def search(self, query: str, top_k: int = 5, category: str | None = None) -> list[dict]:
        candidates = self._filtered_chunks(category)
        if candidates is not self.chunks:
            bm25 = BM25Retriever(candidates)
            vector = VectorRetriever(candidates, embedding_backend=self.embedding_backend)
        else:
            bm25 = self.bm25
            vector = self.vector

        candidate_k = max(top_k * 5, 20)
        if self.retrieval_mode == "bm25":
            results = bm25.search(query, top_k=candidate_k)
            serialized = [_serialize(chunk, score) for chunk, score in results]
        elif self.retrieval_mode in {"vector", "real_embedding"}:
            results = vector.search(query, top_k=candidate_k)
            serialized = [_serialize(chunk, score) for chunk, score in results]
        else:
            bm25_results = bm25.search(query, top_k=candidate_k)
            vector_results = vector.search(query, top_k=candidate_k)
            fused = _rrf([bm25_results, vector_results])
            serialized = [_serialize(chunk, score) for chunk, score in fused]
        return self.reranker.rerank(query, serialized, top_k=top_k)

    def _filtered_chunks(self, category: str | None) -> list[DocumentChunk]:
        if not category:
            return self.chunks
        return [chunk for chunk in self.chunks if chunk.metadata.get("category") == category]


def _rrf(result_sets: list[list[tuple[DocumentChunk, float]]], rank_constant: int = 60):
    scores: dict[str, tuple[DocumentChunk, float]] = {}
    for result_set in result_sets:
        for rank, (chunk, _score) in enumerate(result_set, start=1):
            current = scores.get(chunk.chunk_id, (chunk, 0.0))[1]
            scores[chunk.chunk_id] = (chunk, current + 1.0 / (rank_constant + rank))
    return sorted(scores.values(), key=lambda item: item[1], reverse=True)


def _serialize(chunk: DocumentChunk, score: float) -> dict:
    return {
        "doc_id": chunk.doc_id,
        "chunk_id": chunk.chunk_id,
        "title": chunk.title,
        "content": chunk.content,
        "source_path": chunk.source_path,
        "score": round(score, 6),
        "metadata": chunk.metadata,
    }
