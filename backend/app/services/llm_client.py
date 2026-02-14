from __future__ import annotations

import asyncio
import logging
from typing import Generator

from openai import OpenAI

from app.services.rate_limiter import get_rate_limiter, RateLimitExceededError

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 90,
        rate_limit_enabled: bool = True,
    ):
        kwargs = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model
        self.rate_limit_enabled = rate_limit_enabled

    def _estimate_tokens(self, messages: list[dict]) -> int:
        """Estimate token count for messages (rough approximation)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        # Rough estimate: 1 token ≈ 4 characters
        return max(500, total_chars // 4)

    async def _acquire_rate_limit(self, estimated_tokens: int) -> None:
        """Acquire rate limit permission before making API call."""
        if not self.rate_limit_enabled:
            return

        limiter = get_rate_limiter()
        if not await limiter.acquire(estimated_tokens=estimated_tokens):
            raise RateLimitExceededError(
                "Rate limit exceeded. The system is experiencing high demand. "
                "Please wait a moment and try again."
            )

    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.2,
    ) -> str:
        """Synchronous completion (used by existing code)."""
        # For sync calls, we need to run the async rate limiter
        if self.rate_limit_enabled:
            estimated_tokens = self._estimate_tokens(messages)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, create a task
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._acquire_rate_limit(estimated_tokens)
                        )
                        future.result(timeout=130)
                else:
                    asyncio.run(self._acquire_rate_limit(estimated_tokens))
            except RateLimitExceededError:
                raise
            except Exception as e:
                logger.warning(f"Rate limit check failed, proceeding anyway: {e}")

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=messages,
        )
        return (response.choices[0].message.content or "").strip()

    async def complete_async(
        self,
        messages: list[dict],
        temperature: float = 0.2,
    ) -> str:
        """Async completion with built-in rate limiting."""
        estimated_tokens = self._estimate_tokens(messages)
        await self._acquire_rate_limit(estimated_tokens)

        # Run the sync OpenAI call in a thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=messages,
            )
        )
        return (response.choices[0].message.content or "").strip()

    def stream_complete(
        self,
        messages: list[dict],
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Streaming completion with rate limiting."""
        if self.rate_limit_enabled:
            estimated_tokens = self._estimate_tokens(messages)
            try:
                asyncio.run(self._acquire_rate_limit(estimated_tokens))
            except RateLimitExceededError:
                raise
            except Exception as e:
                logger.warning(f"Rate limit check failed, proceeding anyway: {e}")

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
