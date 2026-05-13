# Corporate Brain — Agentic RAG Enterprise Knowledge Assistant

> An intelligent knowledge assistant that lets employees securely query company documents based on their role, powered by hybrid search, cross-encoder reranking, and a self-correcting agentic loop.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Screenshots](#screenshots)
- [Getting Started](#getting-started)
- [Test Accounts](#test-accounts)
- [RBAC System](#rbac-system)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [License](#license)

---

## Overview

Most enterprise knowledge is scattered across hundreds of documents — HR policies, finance guidelines, IT manuals, and strategy decks. Employees waste time searching through folders or asking colleagues for information that already exists somewhere.

**Corporate Brain** solves this by providing a secure, intelligent assistant that:
- Answers questions in plain English from company documents
- Enforces role-based access control at the vector database level
- Uses an agentic reasoning loop to ensure answer quality
- Supports PDF, DOCX, XLSX, PPTX, and TXT documents
- Runs completely free using Groq LLaMA and local HuggingFace embeddings

---

## Features

- **Hybrid Search** — Combines Qdrant vector search and Elasticsearch BM25 for maximum recall
- **Cross-Encoder Reranking** — ms-marco-MiniLM reranker for high precision results
- **Agentic Plan-Act-Verify Loop** — Self-correcting agent that retries low confidence answers
- **Query Rewriting** — Automatically expands vague queries like "wfh" or "pf"
- **Self-Reflection** — LLM scores its own answer quality before returning it
- **Anti-Hallucination** — Returns "not found" instead of making up answers
- **Role-Based Access Control** — Enforced at vector database level, not just UI
- **Multi-Format Ingestion** — PDF, DOCX, XLSX, PPTX, TXT with OCR fallback
- **Redis Caching** — Repeat queries return instantly from cache
- **Query History** — Every query logged with confidence scores
- **Free to Run** — Groq LLaMA 3.1 (free tier) + local HuggingFace embeddings

---

## Architecture

```
User Query
    │
    ▼
FastAPI Backend
    │
    ▼
JWT Token Validation → Extract User Role
    │
    ▼
Redis Cache Check ──── Cache Hit → Return Instantly
    │ Cache Miss
    ▼
RAG Agent (Plan-Act-Verify Loop)
    │
    ├── PLAN: Analyze query
    │         Rewrite if vague ("wfh" → "work from home policy")
    │
    ├── ACT: Hybrid Search (parallel)
    │         ├── Qdrant Vector Search  ──┐
    │         └── Elasticsearch BM25   ──┴── Reciprocal Rank Fusion
    │                                           │
    │                                           ▼
    │                                   Cross-Encoder Reranking
    │                                   (top 20 → top 8)
    │
    └── VERIFY: Groq LLaMA generates answer
                    │
                    ▼
              Self-Reflection scores answer (0.0 - 1.0)
                    │
              Score >= 0.65 → Accept and return
              Score < 0.65  → Loop back and retry (max 5 times)
                    │
                    ▼
              Save to Redis Cache
                    │
                    ▼
              Response with answer + sources + confidence
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Vite | UI framework |
| Backend | Python 3.11 + FastAPI | REST API |
| LLM | Groq LLaMA 3.1 8B | Answer generation, query rewriting, self-reflection |
| Embeddings | all-MiniLM-L6-v2 | Local text embeddings (384 dimensions) |
| Reranker | ms-marco-MiniLM-L-6-v2 | Cross-encoder reranking |
| Vector DB | Qdrant | Semantic similarity search |
| Search | Elasticsearch 8.12 | BM25 keyword search |
| Database | PostgreSQL 16 | Users, documents, query logs |
| Cache | Redis 7 | Query result caching |
| Auth | JWT + bcrypt | Authentication and password hashing |
| Access Control | Custom RBAC | Role-based document filtering |
| PDF Parsing | pdfplumber + Tesseract | Text, tables, OCR |
| Doc Parsing | python-docx | Word documents |
| Excel Parsing | openpyxl | Spreadsheets |
| PPT Parsing | python-pptx | Presentations |
| Infrastructure | Docker + Docker Compose | Container orchestration |

---

## Screenshots

### Login Screen
![Login](screenshots/login.png)

### Query Interface — Answer with Source Citation
![Query](screenshots/query_answer.png)

### Documents Page — All 8 Documents
![Documents](screenshots/documents.png)

### Access Control — RBAC Matrix
![RBAC](screenshots/rbac.png)

### Query History
![History](screenshots/query_history.png)

### Not Found Response — Anti-Hallucination
![Not Found](screenshots/not_found.png)

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Python 3.11](https://www.python.org/downloads/)
- [Node.js 20](https://nodejs.org/)
- [Groq API Key](https://console.groq.com) — free account

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/corporate-brain.git
cd corporate-brain
```

**2. Create environment file**
```bash
cd backend
cp .env.example .env
```

Open `backend/.env` and add your Groq API key:
```
GROQ_API_KEY=your_groq_api_key_here
```

**3. Start infrastructure services**
```bash
cd corporate-brain
docker compose -f docker/docker-compose.yml up -d qdrant elasticsearch postgres redis
```

Wait 15 seconds for Elasticsearch to fully start, then verify:
```bash
docker ps
# All 4 containers should show "Up"
```

**4. Set up and start backend**
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install aiohttp python-pptx bcrypt==4.0.1

# Start backend
uvicorn api.main:app --reload --port 8000
```

**5. Set up and start frontend**
```bash
cd frontend
npm install
npm run dev
```

**6. Open the app**
```
http://localhost:5173
```

API documentation available at `http://localhost:8000/docs`

---

## Test Accounts

| Username | Password | Role | Documents Accessible |
|----------|----------|------|---------------------|
| admin | Admin@123 | Admin | All 8 documents |
| hr_user | HR@123 | HR | HR Policy + General docs |
| fin_user | Finance@123 | Finance | Finance Policy + General docs |
| employee | Employee@123 | General | General docs only |



---

## RBAC System

Each document is tagged with `allowed_roles` at upload time. Every search query filters by the user's accessible roles **at the vector database level** — not just the UI.

```
Role Hierarchy:
admin   → can access: admin + hr + finance + general documents
hr      → can access: hr + general documents
finance → can access: finance + general documents
general → can access: general documents only
```

**Why this is secure:**
- A Finance user querying for HR data gets zero results
- This is enforced inside Qdrant and Elasticsearch filter conditions
- Even direct API calls bypass the UI but not the database filter
- The data is physically excluded from search results

---

## Project Structure

```
corporate-brain/
├── backend/
│   ├── api/
│   │   └── main.py              # All FastAPI routes and endpoints
│   ├── core/
│   │   ├── config.py            # Centralized settings from .env
│   │   ├── database.py          # SQLAlchemy models and DB connection
│   │   └── embeddings.py        # HuggingFace local embedding service
│   ├── ingestion/
│   │   ├── parser.py            # PDF, DOCX, XLSX, PPTX, TXT parsers
│   │   └── pipeline.py          # Full ingestion pipeline to Qdrant + ES
│   ├── retrieval/
│   │   └── hybrid.py            # Hybrid search + RRF + cross-encoder rerank
│   ├── agents/
│   │   └── rag_agent.py         # Agentic Plan-Act-Verify loop
│   ├── security/
│   │   └── auth.py              # JWT auth + RBAC + password hashing
│   ├── .env.example             # Environment variable template
│   └── requirements.txt         # Python dependencies
├── frontend/
│   └── src/
│       └── App.jsx              # Complete React UI
├── docker/
│   └── docker-compose.yml       # Qdrant, ES, Postgres, Redis
├── screenshots/                 # Project screenshots
├── .gitignore
└── README.md
```

---

## How It Works

### Document Ingestion
```
Upload file → Parse (text + tables + OCR) → Split into 512-token chunks
→ Embed with all-MiniLM-L6-v2 → Store vectors in Qdrant
→ Index text in Elasticsearch → Save metadata in PostgreSQL
```

### Query Processing
```
Query → Check Redis cache → Plan (rewrite if vague)
→ Parallel search (Qdrant + ES) → RRF fusion
→ Cross-encoder rerank → LLaMA generates answer
→ Self-reflection scores answer → Cache result → Return
```

### Supported File Formats

| Format | Parser | Special Features |
|--------|--------|-----------------|
| PDF | pdfplumber | Table extraction, OCR fallback for scanned pages |
| DOCX | python-docx | Paragraph + table extraction, XML fallback |
| XLSX | openpyxl | Multi-sheet support, column header preservation |
| PPTX | python-pptx | Slide-by-slide extraction, speaker notes |
| TXT | Built-in | Direct text extraction |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| GROQ_API_KEY | Groq API key (required) | — |
| JWT_SECRET | Secret key for JWT signing | — |
| DATABASE_URL | PostgreSQL connection string | localhost:5432 |
| QDRANT_URL | Qdrant server URL | localhost:6333 |
| ES_URL | Elasticsearch URL | localhost:9200 |
| REDIS_URL | Redis connection URL | localhost:6379 |
| LLM_MODEL | Groq model name | llama-3.1-8b-instant |
| SELF_REFLECTION_THRESHOLD | Minimum confidence to accept answer | 0.65 |
| TOP_K_VECTOR | Vector search candidates | 20 |
| TOP_K_KEYWORD | Keyword search candidates | 20 |
| TOP_K_RERANK | Final results after reranking | 8 |
| TRANSFORMERS_OFFLINE | Use local model cache only | 1 |

---

## License

MIT License — feel free to use and modify for your own projects.
