from __future__ import annotations

import math
from collections import Counter

from backend.rag.document_loader import DocumentChunk
from backend.rag.tokenizer import tokenize


class BM25Retriever:
    def __init__(self, chunks: list[DocumentChunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(f"{chunk.title}\n{chunk.content}") for chunk in chunks]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avg_doc_length = sum(self.doc_lengths) / max(len(self.doc_lengths), 1)
        self.term_frequencies = [Counter(tokens) for tokens in self.doc_tokens]
        self.doc_frequency: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            self.doc_frequency.update(set(tokens))

    def search(self, query: str, top_k: int = 5) -> list[tuple[DocumentChunk, float]]:
        query_terms = tokenize(query)
        scored: list[tuple[int, float]] = []
        total_docs = len(self.chunks)

        for idx, frequencies in enumerate(self.term_frequencies):
            score = 0.0
            doc_len = self.doc_lengths[idx] or 1
            for term in query_terms:
                tf = frequencies.get(term, 0)
                if tf == 0:
                    continue
                df = self.doc_frequency.get(term, 0)
                idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                score += idf * numerator / denominator
            if score > 0:
                scored.append((idx, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return [(self.chunks[idx], score) for idx, score in scored[:top_k]]
