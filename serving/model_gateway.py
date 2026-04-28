from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass
class LLMGateway:
    base_url: str = os.getenv("OPENAI_BASE_URL", "http://localhost:8001/v1")
    api_key: str = os.getenv("OPENAI_API_KEY", "EMPTY")

    def chat(self, model: str, messages: list[dict], temperature: float = 0.0) -> str:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": model, "messages": messages, "temperature": temperature},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
