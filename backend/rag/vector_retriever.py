from backend.rag.document_loader import DocumentChunk
from backend.rag.embeddings import EmbeddingBackend, make_embedding_backend


class VectorRetriever:
    def __init__(self, chunks: list[DocumentChunk], embedding_backend: EmbeddingBackend | None = None) -> None:
        self.chunks = chunks
        self.embedding_backend = embedding_backend or make_embedding_backend()
        self.vectors = self.embedding_backend.embed_texts(
            [f"{chunk.title}\n{chunk.content}" for chunk in chunks]
        )

    def search(self, query: str, top_k: int = 5) -> list[tuple[DocumentChunk, float]]:
        query_vector = self.embedding_backend.embed_texts([query])[0]
        scored = [
            (chunk, _cosine(query_vector, vector)) for chunk, vector in zip(self.chunks, self.vectors)
        ]
        scored = [item for item in scored if item[1] > 0]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


HashVectorRetriever = VectorRetriever
