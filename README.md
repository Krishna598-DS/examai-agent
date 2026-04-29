# ExamAI Agent

A production-grade multi-agent AI system for autonomous research on Indian 
competitive exams (JEE and UPSC). Built with FastAPI, LangGraph, ChromaDB, 
and Redis.

## What it does

A user asks a question. The system autonomously:

1. Searches the web for relevant content (Serper API + full page scraping)
2. Retrieves from indexed NCERT and UPSC study material (RAG via ChromaDB)
3. Cross-verifies facts across both sources (confidence scoring)
4. Self-corrects if confidence is below threshold (query reformulation)
5. Returns a verified, sourced answer with confidence score

## Benchmark Results

Evaluated on 33 curated questions across JEE and UPSC categories.

| Metric | Score |
|--------|-------|
| RAGAS Score | 0.581 |
| Verification Rate | 72.7% |
| Avg Confidence | 0.723 |
| Faithfulness | 0.751 |
| Answer Relevancy | 0.773 |
| Context Precision | 0.602 |
| Avg Latency (first call) | 20.4s |
| Avg Latency (cached) | <1ms |
| Cache speedup | ~67,000x |

### By Category

| Category | RAGAS Score | Verification Rate |
|----------|-------------|-------------------|
| UPSC History | 0.694 | 100% |
| UPSC Polity | 0.630 | 80% |
| JEE Math | 0.585 | 80% |
| JEE Chemistry | 0.562 | 70% |
| JEE Physics | 0.540 | 60% |

### Score Progression (engineering iterations)

| Run | RAGAS | Verification | Change |
|-----|-------|--------------|--------|
| Baseline (5 chunks) | 0.364 | 10% | — |
| After content indexing | 0.418 | 25% | +15% |
| After chunk size tuning | 0.462 | 30% | +27% |
| Full 33-question eval | 0.495 | 45.5% | +36% |
| After failure analysis | 0.581 | 72.7% | +60% |

## Architecture

```
User Question (POST /api/v1/ask)
         │
         ▼
    Redis Cache ──── HIT ──── Return instantly (<1ms)
         │
        MISS
         │
         ▼
   Orchestrator (LangGraph)
         │
    asyncio.gather()
    ┌────┴────┐
    │         │
Search      PDF
Agent      Agent
(Serper    (ChromaDB
+ scrape)   RAG)
    │         │
    └────┬────┘
         │
         ▼
   Verifier Agent
   (confidence score
    + self-correction)
         │
         ▼
  Verified Answer
  {verdict, confidence,
   final_answer, sources}
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API | FastAPI + Uvicorn | Async, auto-docs, production-grade |
| Agents | LangGraph + OpenAI gpt-4o-mini | Stateful agent graphs |
| Vector DB | ChromaDB | Local, persistent, cosine similarity |
| Embeddings | all-MiniLM-L6-v2 | Free, local, fast |
| Cache | Redis | Shared, persistent, native TTL |
| PDF parsing | PyMuPDF | Fastest Python PDF library |
| Web search | Serper API | Structured Google results |
| Logging | structlog | JSON structured logs |
| Testing | pytest + pytest-asyncio | Async test support |
| Container | Docker + Docker Compose | Reproducible deployment |

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/examai-agent.git
cd examai-agent

# Setup
cp .env.example .env
# Add your OPENAI_API_KEY and SERPER_API_KEY to .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run
docker compose up redis -d
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Index study material
curl -X POST http://localhost:8000/api/v1/pdf/index-all

# Ask a question
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Newtons second law of motion?"}'
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/ask` | Main orchestrator endpoint |
| POST | `/api/v1/search` | Search agent only |
| POST | `/api/v1/pdf/query` | PDF RAG only |
| POST | `/api/v1/pdf/index` | Index a PDF file |
| POST | `/api/v1/pdf/index-all` | Index all PDFs |
| GET | `/api/v1/pdf/stats` | Vector store stats |
| GET | `/api/v1/cache/stats` | Redis cache stats |
| DELETE | `/api/v1/cache` | Clear cache |
| GET | `/api/v1/orchestrator/stats` | Orchestrator stats |

## Key Engineering Decisions

**Why LangGraph over raw LangChain agents?**
LangGraph models agents as stateful graphs with explicit nodes and edges.
This makes the agent loop debuggable, testable, and extensible. Raw
LangChain agents have opaque state management that's hard to inspect.

**Why local embeddings over OpenAI embeddings?**
`all-MiniLM-L6-v2` runs locally with no API cost. For development and
moderate scale, the quality difference doesn't justify the per-token cost.
In production I'd benchmark both and choose based on retrieval quality metrics.

**Why cache at orchestrator level?**
A cache hit skips all three agents — maximum latency and cost savings.
Agent-level caching would still run orchestration logic. The orchestrator
cache stores verified, confidence-scored answers — the highest-quality artifact.

**Why chunk size 800 over 500?**
Larger chunks keep conceptually related sentences together. 500-character
chunks frequently split mid-concept, reducing retrieval precision. 800
characters with 100-character overlap gave better RAGAS scores in evaluation.

**How hallucination is prevented?**
Two layers: RAG constrains the PDF agent to answer only from retrieved
chunks. The verifier cross-checks the PDF answer against web search and
scores confidence. Answers below 0.5 confidence trigger self-correction
with reformulated queries.

## Project Structure

```
examai-agent/
├── app/
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── config.py            # Pydantic Settings, environment config
│   ├── logger.py            # structlog JSON logging
│   ├── exceptions.py        # Custom exception hierarchy
│   ├── agents/
│   │   ├── search_agent.py  # LangGraph ReAct search agent
│   │   ├── pdf_agent.py     # RAG pipeline agent
│   │   └── verifier_agent.py # Cross-verification + self-correction
│   ├── orchestrator/
│   │   └── graph.py         # Multi-agent coordinator + caching
│   ├── api/
│   │   └── routes.py        # FastAPI route definitions
│   └── tools/
│       ├── web_search.py    # Serper API + BeautifulSoup scraping
│       ├── pdf_reader.py    # PyMuPDF extraction + chunking
│       ├── vector_store.py  # ChromaDB operations
│       ├── cache.py         # Redis async cache
│       ├── retry.py         # Exponential backoff with jitter
│       └── rate_limiter.py  # Sliding window rate limiter
├── eval/
│   ├── questions.json       # 200-question benchmark dataset
│   ├── run_eval.py          # Evaluation harness
│   ├── metrics.py           # RAGAS-style metrics computation
│   └── results_v2.json      # Latest benchmark results
├── tests/
│   └── test_retry.py        # Unit tests (4 passing)
├── data/
│   ├── pdfs/                # Study material PDFs
│   └── chroma/              # ChromaDB persistent storage
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Evaluation Methodology

Questions are categorized by subject and difficulty (easy/medium/hard).
Each question has a manually written ground truth answer.

Metrics computed:
- **Faithfulness** — are claims grounded in retrieved sources?
- **Answer Relevancy** — does the answer address the question?  
- **Context Recall** — did retrieval find relevant content?
- **Context Precision** — were retrieved chunks useful?
- **RAGAS Score** — average of all four metrics

## Author

Built as a portfolio project targeting MAANG-level AI engineering roles.
Demonstrates: multi-agent orchestration, RAG pipelines, production API design,
evaluation-driven development, and Docker deployment.
