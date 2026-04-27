# app/exceptions.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.logger import get_logger

logger = get_logger(__name__)


# Custom exception classes for our domain
# Why custom exceptions? They carry semantic meaning.
# "AgentTimeoutError" tells you exactly what went wrong.
# A generic "Exception" tells you nothing.

class ExamAIException(Exception):
    """Base exception for all ExamAI errors."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class AgentTimeoutError(ExamAIException):
    """Raised when an agent takes too long to respond."""
    pass


class AgentError(ExamAIException):
    """Raised when an agent fails for any reason."""
    pass


class SearchError(ExamAIException):
    """Raised when the web search tool fails."""
    pass


class PDFReadError(ExamAIException):
    """Raised when PDF parsing fails."""
    pass


class VerificationError(ExamAIException):
    """Raised when the verification agent fails."""
    pass


# FastAPI exception handlers — these catch exceptions and turn them
# into proper HTTP responses with correct status codes

async def examai_exception_handler(
    request: Request,
    exc: ExamAIException
) -> JSONResponse:
    """Handle all our custom exceptions."""
    logger.error(
        "examai_exception",
        error_type=type(exc).__name__,
        message=exc.message,
        details=exc.details,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "details": exc.details,
        }
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """Handle FastAPI's built-in HTTP exceptions (404, 422, etc.)"""
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "message": exc.detail,
        }
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Catch-all for any exception we didn't anticipate.
    Logs the full traceback, returns a safe generic message to the user.
    Why safe? You never want to expose internal Python tracebacks to users —
    they can reveal system internals that aid attackers.
    """
    logger.exception(
        "unhandled_exception",
        error_type=type(exc).__name__,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please try again.",
        }
    )
