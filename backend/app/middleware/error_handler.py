from __future__ import annotations

import logging
import traceback
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.rate_limiter import RateLimitExceededError

logger = logging.getLogger("rfp_platform")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except RateLimitExceededError as exc:
            # Return 429 Too Many Requests for rate limit errors
            logger.warning(
                "Rate limit exceeded for %s %s: %s",
                request.method,
                request.url.path,
                str(exc),
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": str(exc),
                    "retry_after": 30,  # Suggest retry after 30 seconds
                },
                headers={"Retry-After": "30"},
            )
        except Exception as exc:
            error_id = uuid4().hex[:8]
            logger.error(
                "Unhandled error [%s] %s %s: %s\n%s",
                error_id,
                request.method,
                request.url.path,
                str(exc),
                traceback.format_exc(),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error_id": error_id,
                },
            )
