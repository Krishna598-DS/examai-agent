# ExamAI Agent

A production-grade multi-agent AI system for autonomous research on Indian competitive exams (JEE and UPSC).

## What it does

A user asks a question. The system autonomously:
1. Searches the web for relevant content
2. Reads and retrieves from NCERT and UPSC PDF documents
3. Cross-verifies facts across multiple sources
4. Self-corrects if confidence is low
5. Returns a verified, sourced answer

Benchmarked on a curated 200-question evaluation set across JEE (Physics, Chemistry, Math) and UPSC (History, Polity, Economics, Current Affairs).

## Architecture

User Question
│
▼
Orchestrator (LangGraph)
│
├──► Search Agent (Serper API + BeautifulSoup)
│
├──► PDF Agent (PyMuPDF + ChromaDB RAG)
│
└──► Verifier Agent (multi-source cross-check)
│
▼
Verified Answer

## Tech Stack

- **Runtime:** Python 3.12, FastAPI, Uvicorn (ASGI)
- **Agents:** LangGraph, LangChain, OpenAI API
- **Storage:** ChromaDB (vector store), Redis (cache)
- **Evaluation:** RAGAS metrics, 200-question benchmark
- **Observability:** structlog, LangSmith tracing
- **Infrastructure:** Docker, Docker Compose, GitHub Actions CI

## Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/examai-agent.git
cd examai-agent

# Copy environment variables
cp .env.example .env
# Edit .env and add your API keys

# Run with Docker Compose
docker compose up -d

# Test the API
curl http://localhost:8000/health
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Service info |
| GET | `/health` | Health check |
| POST | `/api/v1/query` | Ask a question (available from Week 2) |

