from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="RFP Response Platform", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Import and include routers
from app.routers import auth, chat, export, knowledge, organizations, projects  # noqa: E402

app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(projects.router)
app.include_router(chat.router)
app.include_router(export.router)
app.include_router(knowledge.router)


@app.get("/health")
async def health() -> dict:
    db_ok = False
    try:
        from app.database import async_session
        from sqlalchemy import text
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
    status = "ok" if db_ok else "degraded"
    return {"status": status, "version": "2.0.0", "database": "connected" if db_ok else "unavailable"}
