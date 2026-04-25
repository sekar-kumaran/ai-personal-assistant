from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from src.config import settings


class LLMClient(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...


@dataclass
class MockLLMClient:
    model: str = settings.llm_model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return (
            "Showcase response: I parsed your request and would route it through the "
            f"assistant pipeline. Model={self.model}. "
            f"Prompt summary={user_prompt[:180]}"
        )


@dataclass
class OllamaLLMClient:
    model: str = settings.llm_model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import ollama
        except ImportError:
            return MockLLMClient(self.model).generate(system_prompt, user_prompt)

        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response["message"]["content"]


def get_llm_client() -> LLMClient:
    if settings.llm_provider.lower() == "ollama":
        return OllamaLLMClient()
    return MockLLMClient()
