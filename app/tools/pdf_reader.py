# app/tools/pdf_reader.py
import fitz
import re
from pathlib import Path
from typing import List
from dataclasses import dataclass
from app.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PDFChunk:
    text: str
    source: str
    page: int
    chunk_index: int
    total_chunks: int


def extract_text_from_pdf(pdf_path: str) -> List[dict]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info("pdf_extraction_started", path=str(path))
    pages = []

    with fitz.open(pdf_path) as doc:
        logger.info("pdf_opened", pages=len(doc), filename=path.name)
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            text = clean_pdf_text(text)
            if text.strip():
                pages.append({
                    "page": page_num,
                    "text": text,
                    "source": path.name
                })

    logger.info("pdf_extraction_completed",
                filename=path.name,
                pages_extracted=len(pages))
    return pages


def clean_pdf_text(text: str) -> str:
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_text(
    pages: List[dict],
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[PDFChunk]:
    chunks = []
    chunk_index = 0

    for page_data in pages:
        text = page_data["text"]
        page_num = page_data["page"]
        source = page_data["source"]

        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                boundary = text.rfind('.', end - 100, end)
                if boundary != -1:
                    end = boundary + 1

            chunk_text_content = text[start:end].strip()
            if chunk_text_content:
                chunks.append(PDFChunk(
                    text=chunk_text_content,
                    source=source,
                    page=page_num,
                    chunk_index=chunk_index,
                    total_chunks=0
                ))
                chunk_index += 1

            start = end - chunk_overlap

    total = len(chunks)
    for chunk in chunks:
        chunk.total_chunks = total

    logger.info("chunking_completed", total_chunks=total)
    return chunks
