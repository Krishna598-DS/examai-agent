# app/api/routes.py
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.agents.search_agent import search_agent
from app.agents.pdf_agent import pdf_agent
from app.tools.vector_store import vector_store
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["agents"])


class QueryRequest(BaseModel):
    question: str = Field(
        min_length=10,
        max_length=500,
        examples=["What is Newton's second law of motion?"]
    )


class IndexRequest(BaseModel):
    pdf_path: str = Field(
        description="Path to PDF file relative to project root",
        examples=["data/pdfs/sample_physics.pdf"]
    )


@router.post("/search")
async def search_endpoint(request: QueryRequest):
    """Search the web for an answer to a JEE/UPSC question."""
    logger.info("search_endpoint_called", question=request.question[:100])
    return await search_agent.run(request.question)


@router.post("/pdf/index")
async def index_pdf(request: IndexRequest):
    """Index a single PDF file into the vector store."""
    logger.info("index_endpoint_called", path=request.pdf_path)
    return await pdf_agent.index_pdf(request.pdf_path)


@router.post("/pdf/index-all")
async def index_all_pdfs():
    """Index all PDFs in the data/pdfs directory."""
    return await pdf_agent.index_all_pdfs()


@router.post("/pdf/query")
async def pdf_query(request: QueryRequest):
    """Answer a question using indexed PDF content via RAG."""
    logger.info("pdf_query_called", question=request.question[:100])
    return await pdf_agent.run(request.question)


@router.get("/pdf/stats")
async def pdf_stats():
    """Get vector store statistics."""
    return vector_store.get_stats()
