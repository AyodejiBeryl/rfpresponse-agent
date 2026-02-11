from __future__ import annotations

from typing import Generator

from openai import OpenAI


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 90,
    ):
        kwargs = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.2,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=messages,
        )
        return (response.choices[0].message.content or "").strip()

    def stream_complete(
        self,
        messages: list[dict],
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=messages,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
