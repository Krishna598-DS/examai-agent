# app/agents/pdf_agent.py
import asyncio
import time
from pathlib import Path
from typing import List
from app.tools.pdf_reader import extract_text_from_pdf, chunk_text
from app.tools.vector_store import vector_store
from app.config import settings
from app.logger import get_logger
from app.exceptions import PDFReadError, AgentError

logger = get_logger(__name__)


class PDFAgent:

    def __init__(self):
        self.pdf_dir = Path("data/pdfs")
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        logger.info("pdf_agent_initialized", pdf_dir=str(self.pdf_dir))

    async def index_pdf(self, pdf_path: str) -> dict:
        try:
            loop = asyncio.get_event_loop()
            pages = await loop.run_in_executor(
                None, extract_text_from_pdf, pdf_path
            )
            chunks = await loop.run_in_executor(
                None, chunk_text, pages
            )
            added = vector_store.add_chunks(chunks)
            return {
                "pdf": Path(pdf_path).name,
                "pages": len(pages),
                "chunks_created": len(chunks),
                "chunks_added": added,
                "already_indexed": added == 0
            }
        except FileNotFoundError as e:
            raise PDFReadError(str(e))
        except Exception as e:
            raise PDFReadError(
                f"Failed to index PDF: {str(e)}",
                details={"path": pdf_path}
            )

    async def index_all_pdfs(self) -> List[dict]:
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        if not pdf_files:
            logger.warning("no_pdfs_found", directory=str(self.pdf_dir))
            return []
        results = []
        for pdf_path in pdf_files:
            result = await self.index_pdf(str(pdf_path))
            results.append(result)
        return results

    async def run(self, question: str, top_k: int = 5) -> dict:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        start = time.time()
        logger.info("pdf_agent_started", question=question[:100])

        chunks = vector_store.search(question, top_k=top_k)

        if not chunks:
            return {
                "answer": "No relevant content found in indexed PDFs. Please index PDFs first using /api/v1/pdf/index-all",
                "agent": "pdf",
                "sources": [],
                "chunks_retrieved": 0,
                "duration_seconds": round(time.time() - start, 2),
                "question": question,
            }

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {i}: {chunk['source']}, Page {chunk['page']}]\n{chunk['text']}"
            )
        context = "\n\n".join(context_parts)

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )

        messages = [
            SystemMessage(content="""You are an expert tutor for Indian competitive 
exams (JEE and UPSC). Answer using ONLY the provided context.
Always cite source and page number. If context is insufficient, say so clearly."""),
            HumanMessage(content=f"""Context from study materials:
{context}

Question: {question}

Answer based strictly on the above context:""")
        ]

        response = await llm.ainvoke(messages)
        sources = list({f"{c['source']} (Page {c['page']})" for c in chunks})
        duration = round(time.time() - start, 2)

        logger.info("pdf_agent_completed",
                   chunks_retrieved=len(chunks),
                   duration_seconds=duration)

        return {
            "answer": response.content,
            "agent": "pdf",
            "sources": sources,
            "chunks_retrieved": len(chunks),
            "top_similarity": chunks[0]["similarity"] if chunks else 0,
            "duration_seconds": duration,
            "question": question,
        }


pdf_agent = PDFAgent()
