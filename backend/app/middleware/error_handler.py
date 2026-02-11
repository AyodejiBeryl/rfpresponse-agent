from __future__ import annotations

import logging
import traceback
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("rfp_platform")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
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
