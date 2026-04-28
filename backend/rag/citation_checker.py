from __future__ import annotations

from backend.rag.tokenizer import tokenize


class CitationChecker:
    def check(self, draft: str, cited_chunks: list[dict], min_overlap: int = 2) -> dict:
        cited_ids = {chunk["chunk_id"] for chunk in cited_chunks}
        draft_tokens = set(tokenize(draft))
        weak_citations: list[str] = []
        for chunk in cited_chunks:
            chunk_tokens = set(tokenize(chunk["title"] + "\n" + chunk["content"]))
            overlap = draft_tokens & chunk_tokens
            if len(overlap) < min_overlap:
                weak_citations.append(chunk["chunk_id"])

        return {
            "has_citations": bool(cited_chunks),
            "cited_chunk_ids": sorted(cited_ids),
            "weak_citations": weak_citations,
            "citation_accuracy": 1.0 if cited_chunks and not weak_citations else 0.0,
        }
