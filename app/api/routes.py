# app/api/routes.py
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.agents.search_agent import search_agent
from app.logger import get_logger

logger = get_logger(__name__)

# APIRouter is like a mini FastAPI app
# We define routes here and register them in main.py
# Why? Keeps main.py clean. Each feature gets its own router file.
router = APIRouter(prefix="/api/v1", tags=["agents"])


class QueryRequest(BaseModel):
    question: str = Field(
        description="The JEE or UPSC question to research",
        min_length=10,
        max_length=500,
        examples=["What is Newton's second law of motion?"]
    )


class QueryResponse(BaseModel):
    answer: str
    agent: str
    duration_seconds: float
    question: str


@router.post("/search", response_model=QueryResponse)
async def search_endpoint(request: QueryRequest):
    """
    Ask a JEE or UPSC question. The search agent will autonomously
    search the web and return a sourced answer.
    """
    logger.info("search_endpoint_called", question=request.question[:100])
    result = await search_agent.run(request.question)
    return QueryResponse(**result)
