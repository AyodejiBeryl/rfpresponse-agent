"""
Rate limiter for LLM API calls to prevent exceeding Groq/OpenAI limits.

Uses a token bucket algorithm with async queuing for requests that exceed limits.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 30  # Max requests per minute
    tokens_per_minute: int = 6000  # Max tokens per minute (Groq free tier)
    max_queue_size: int = 50  # Max requests to queue before rejecting
    queue_timeout: float = 120.0  # Max seconds to wait in queue


@dataclass
class RateLimiter:
    """
    Token bucket rate limiter with async request queuing.

    Tracks both request count and estimated token usage to stay within limits.
    """
    config: RateLimiterConfig = field(default_factory=RateLimiterConfig)

    # Token bucket state
    _request_tokens: float = field(default=0, init=False)
    _token_tokens: float = field(default=0, init=False)
    _last_update: float = field(default_factory=time.time, init=False)

    # Queue management
    _queue: asyncio.Queue = field(default=None, init=False)
    _lock: asyncio.Lock = field(default=None, init=False)
    _initialized: bool = field(default=False, init=False)

    # Stats
    _total_requests: int = field(default=0, init=False)
    _queued_requests: int = field(default=0, init=False)
    _rejected_requests: int = field(default=0, init=False)

    def _ensure_initialized(self):
        """Lazy initialization of async primitives."""
        if not self._initialized:
            self._queue = asyncio.Queue(maxsize=self.config.max_queue_size)
            self._lock = asyncio.Lock()
            self._request_tokens = float(self.config.requests_per_minute)
            self._token_tokens = float(self.config.tokens_per_minute)
            self._initialized = True

    def _refill_tokens(self):
        """Refill token buckets based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._last_update = now

        # Refill request tokens (requests per minute)
        self._request_tokens = min(
            self.config.requests_per_minute,
            self._request_tokens + (elapsed / 60.0) * self.config.requests_per_minute
        )

        # Refill token tokens (LLM tokens per minute)
        self._token_tokens = min(
            self.config.tokens_per_minute,
            self._token_tokens + (elapsed / 60.0) * self.config.tokens_per_minute
        )

    def _can_proceed(self, estimated_tokens: int = 1000) -> bool:
        """Check if request can proceed immediately."""
        self._refill_tokens()
        return self._request_tokens >= 1 and self._token_tokens >= estimated_tokens

    def _consume(self, estimated_tokens: int = 1000):
        """Consume tokens for a request."""
        self._request_tokens -= 1
        self._token_tokens -= estimated_tokens
        self._total_requests += 1

    async def acquire(
        self,
        estimated_tokens: int = 1000,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Acquire permission to make an LLM request.

        Args:
            estimated_tokens: Estimated token usage for this request
            timeout: Max seconds to wait (defaults to config.queue_timeout)

        Returns:
            True if permission granted, False if rejected/timeout
        """
        self._ensure_initialized()
        timeout = timeout or self.config.queue_timeout

        async with self._lock:
            # Check if we can proceed immediately
            if self._can_proceed(estimated_tokens):
                self._consume(estimated_tokens)
                logger.debug(f"Rate limit: immediate proceed (req_tokens={self._request_tokens:.1f})")
                return True

            # Check queue capacity
            if self._queue.qsize() >= self.config.max_queue_size:
                self._rejected_requests += 1
                logger.warning(f"Rate limit: request rejected (queue full)")
                return False

        # Queue the request and wait
        self._queued_requests += 1
        event = asyncio.Event()

        try:
            start_time = time.time()

            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Rate limit: request timed out after {elapsed:.1f}s")
                    return False

                # Wait a bit then retry
                await asyncio.sleep(0.5)

                async with self._lock:
                    if self._can_proceed(estimated_tokens):
                        self._consume(estimated_tokens)
                        logger.debug(f"Rate limit: proceed after {elapsed:.1f}s wait")
                        return True

        finally:
            self._queued_requests -= 1

    def get_stats(self) -> dict:
        """Get current rate limiter statistics."""
        self._ensure_initialized()
        self._refill_tokens()

        return {
            "requests_available": round(self._request_tokens, 1),
            "tokens_available": round(self._token_tokens, 0),
            "total_requests": self._total_requests,
            "queued_requests": self._queued_requests,
            "rejected_requests": self._rejected_requests,
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "tokens_per_minute": self.config.tokens_per_minute,
            }
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            config=RateLimiterConfig(
                requests_per_minute=30,  # Conservative for Groq free tier
                tokens_per_minute=5000,  # Leave buffer below 6000 limit
                max_queue_size=50,
                queue_timeout=120.0,
            )
        )
    return _rate_limiter


async def rate_limited_llm_call(func, *args, estimated_tokens: int = 2000, **kwargs):
    """
    Wrapper for rate-limited LLM calls.

    Usage:
        result = await rate_limited_llm_call(
            llm_client.complete,
            prompt="...",
            estimated_tokens=1500
        )
    """
    limiter = get_rate_limiter()

    if not await limiter.acquire(estimated_tokens=estimated_tokens):
        raise RateLimitExceededError(
            "LLM rate limit exceeded. Please try again in a few moments."
        )

    return await func(*args, **kwargs)


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded and request cannot be queued."""
    pass
