# app/main.py
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Configure structured logging
# structlog outputs JSON instead of plain text
# JSON logs can be searched, filtered, and sent to monitoring tools
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Create the FastAPI app using values from our config
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent research system for JEE and UPSC exam preparation"
)

# CORS middleware — required if a browser frontend will call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event — runs once when the server starts
# Use this for: connecting to databases, loading models, warming up caches
@app.on_event("startup")
async def startup_event():
    logger.info("server_starting", app=settings.app_name, version=settings.app_version)

# Root endpoint
@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }

# Health check — monitoring tools ping this URL to know if your service is alive
@app.get("/health")
async def health():
    return {"status": "ok"}
