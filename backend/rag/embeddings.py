from __future__ import annotations

import hashlib
import math
import os
from abc import ABC, abstractmethod

from backend.rag.tokenizer import tokenize


class EmbeddingBackend(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class HashEmbeddingBackend(EmbeddingBackend):
    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class SentenceTransformerEmbeddingBackend(EmbeddingBackend):
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Install it with "
                "`pip install -e '.[rag]'` or set EMBEDDING_BACKEND=hash."
            ) from exc

        try:
            self.model = SentenceTransformer(model_name)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load embedding model {model_name!r}. "
                "Check network/cache access or set EMBEDDING_BACKEND=hash."
            ) from exc

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [vector.tolist() for vector in vectors]


def make_embedding_backend(
    backend: str | None = None, model_name: str | None = None
) -> EmbeddingBackend:
    selected = (backend or os.getenv("EMBEDDING_BACKEND", "hash")).lower()
    if selected == "hash":
        return HashEmbeddingBackend()
    if selected == "sentence_transformer":
        return SentenceTransformerEmbeddingBackend(
            model_name or os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
        )
    raise ValueError(f"Unsupported EMBEDDING_BACKEND={selected!r}")
