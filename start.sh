#!/bin/bash
set -e

echo "Starting ExamAI Agent..."

python3 -c "
import sys
sys.path.insert(0, '.')
from app.tools.vector_store import vector_store
from app.tools.pdf_reader import extract_text_from_pdf, chunk_text
from pathlib import Path

count = vector_store.collection.count()
print(f'Vector store has {count} chunks')

if count == 0:
    print('Indexing PDFs...')
    pdf_dir = Path('data/pdfs')
    pdfs = list(pdf_dir.glob('*.pdf'))
    print(f'Found {len(pdfs)} PDFs')
    for pdf in pdfs:
        try:
            pages = extract_text_from_pdf(str(pdf))
            chunks = chunk_text(pages)
            added = vector_store.add_chunks(chunks)
            print(f'Indexed {pdf.name}: {added} chunks')
        except Exception as e:
            print(f'Failed {pdf.name}: {e}')
    print(f'Total chunks: {vector_store.collection.count()}')
else:
    print('Already indexed, skipping')
"

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1
