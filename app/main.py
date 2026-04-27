# app/main.py
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
import asyncio
import time

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# "lifespan" is the modern FastAPI way to handle startup and shutdown.
# @asynccontextmanager makes it work with Python's "async with" pattern.
# The code BEFORE "yield" runs on startup.
# The code AFTER "yield" runs on shutdown.
# Why better than @app.on_event? It's a single function that handles
# both startup and shutdown, and it's the official Python async pattern.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("server_starting",
                app=settings.app_name,
                version=settings.app_version)
    yield
    # Shutdown — we'll add cleanup here later (close DB connections, etc.)
    logger.info("server_stopping")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent research system for JEE and UPSC exam preparation",
    lifespan=lifespan  # Pass the lifespan handler here
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/demo/concurrent")
async def demo_concurrent():
    """
    This endpoint demonstrates why async matters.
    It runs three simulated agent calls concurrently.
    Without async this would take 6 seconds.
    With asyncio.gather() it takes 3 seconds.
    """
    
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
    
    # All three run simultaneously — total time = max(2, 3, 1) = 3 seconds
    search_result, pdf_result, verify_result = await asyncio.gather(
        fake_search("JEE Physics", delay=2),
        fake_pdf("ncert.pdf", delay=3),
        fake_verify("Newton's 2nd law", delay=1),
    )
    
    elapsed = round(time.time() - start, 2)
    
    return {
        "elapsed_seconds": elapsed,
        "note": "Three agents ran concurrently. Total = slowest agent, not sum.",
        "results": [search_result, pdf_result, verify_result]
    }
