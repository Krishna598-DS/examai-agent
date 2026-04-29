# app/main.py
import asyncio
import time
from contextlib import asynccontextmanager
from app.tools.cache import redis_cache
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.config import settings
from app.logger import setup_logging, get_logger
from app.exceptions import (
    ExamAIException,
    examai_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)

# Setup logging FIRST before anything else
# Why first? Any error during startup should also be logged properly
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(
        "server_starting",
        app=settings.app_name,
        version=settings.app_version,
        env=settings.env,
        debug=settings.debug,
    )
    # Connect to Redis
    await redis_cache.connect()
    yield
    # Shutdown
    await redis_cache.disconnect()
    logger.info("server_stopping", app=settings.app_name)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent research system for JEE and UPSC exam preparation",
    lifespan=lifespan,
    # In production, hide the /docs and /redoc endpoints
    # Exposing API docs publicly can aid attackers
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# Register exception handlers
# Order matters — more specific exceptions first
app.add_exception_handler(ExamAIException, examai_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
@app.get("/")
async def root():
    logger.info("root_endpoint_called")
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.env,
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.env}


@app.get("/demo/concurrent")
async def demo_concurrent():
    """Demonstrates async concurrency with simulated agent calls."""

    async def fake_search(query: str, delay: float):
        await asyncio.sleep(delay)
        return {"agent": "search", "query": query, "delay": delay}

    async def fake_pdf(filename: str, delay: float):
        await asyncio.sleep(delay)
        return {"agent": "pdf", "filename": filename, "delay": delay}

    async def fake_verify(claim: str, delay: float):
        await asyncio.sleep(delay)
        return {"agent": "verify", "claim": claim, "delay": delay}

    start = time.time()
    search_result, pdf_result, verify_result = await asyncio.gather(
        fake_search("JEE Physics", delay=2),
        fake_pdf("ncert.pdf", delay=3),
        fake_verify("Newton's 2nd law", delay=1),
    )

    return {
        "elapsed_seconds": round(time.time() - start, 2),
        "note": "Three agents ran concurrently. Total = slowest, not sum.",
        "results": [search_result, pdf_result, verify_result],
    }


@app.get("/demo/error")
async def demo_error():
    """
    Demonstrates error handling.
    Intentionally raises an exception to show how it's caught and formatted.
    """
    logger.warning("demo_error_endpoint_called")
    raise ExamAIException(
        message="This is a demo error",
        details={"hint": "This was intentional", "endpoint": "/demo/error"}
    )
