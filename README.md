# Corporate Brain — Agentic RAG Knowledge Assistant

An enterprise knowledge assistant that lets employees securely query
company documents based on their role using hybrid search,
cross-encoder reranking, and a self-correcting agent loop.

## Features

- Hybrid search combining Qdrant vector search and Elasticsearch BM25
- Cross-encoder reranking using ms-marco-MiniLM
- Agentic Plan-Act-Verify loop with query rewriting and self-reflection
- Role-Based Access Control enforced at vector database level
- Multi-format document ingestion — PDF, DOCX, XLSX, PPTX, TXT
- OCR fallback for scanned PDFs using Tesseract
- Redis query result caching for instant repeat responses
- Free LLM using Groq LLaMA 3.1 and local HuggingFace embeddings

## Tech Stack

**Frontend:** React, Vite  
**Backend:** Python, FastAPI, Uvicorn  
**AI/ML:** Groq LLaMA 3.1, all-MiniLM-L6-v2, ms-marco cross-encoder  
**Databases:** Qdrant, Elasticsearch, PostgreSQL, Redis  
**Auth:** JWT, RBAC  
**Infrastructure:** Docker, Docker Compose

## Architecture

```
User Query → FastAPI → JWT Auth → RAG Agent
                                      ↓
                              Plan (query rewrite)
                                      ↓
                         Qdrant + Elasticsearch (parallel)
                                      ↓
                         Reciprocal Rank Fusion
                                      ↓
                         Cross-encoder reranking
                                      ↓
                         Groq LLaMA answer generation
                                      ↓
                         Self-reflection scoring
                                      ↓
                         Redis cache → Response
```

## Setup

### Prerequisites

- Docker Desktop
- Python 3.11
- Node.js 20
- Groq API key (free at console.groq.com)

### Installation

1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/corporate-brain.git
cd corporate-brain
```

2. Create environment file

```bash
cp backend/.env.example backend/.env
# Add your GROQ_API_KEY to backend/.env
```

3. Start infrastructure

```bash
docker compose -f docker/docker-compose.yml up -d qdrant elasticsearch postgres redis
```

4. Install backend dependencies

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

5. Start backend

```bash
uvicorn api.main:app --reload --port 8000
```

6. Install and start frontend

```bash
cd frontend
npm install
npm run dev
```

7. Open http://localhost:5173

## Test Accounts

| Username | Password     | Role    | Access            |
| -------- | ------------ | ------- | ----------------- |
| admin    | Admin@123    | Admin   | All documents     |
| hr_user  | HR@123       | HR      | HR + General      |
| fin_user | Finance@123  | Finance | Finance + General |
| employee | Employee@123 | General | General only      |

## RBAC Architecture

Each document is tagged with allowed roles at upload time.
Every search query filters by the user's role at the vector
database level — not just the UI. Unauthorized data is
invisible even to direct API calls.

## License

MIT

```

---

## Part 4 — Create .env.example

Create `D:\corporate-brain\backend\.env.example` — this shows others what env vars are needed without exposing your actual keys:
```

GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET=your_random_secret_key_here
QDRANT_URL=http://localhost:6333
ES_URL=http://localhost:9200
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql+asyncpg://brain:brain_secret@localhost:5432/corporate_brain
LLM_MODEL=llama-3.1-8b-instant
SELF_REFLECTION_THRESHOLD=0.55
TOP_K_VECTOR=20
TOP_K_KEYWORD=20
TOP_K_RERANK=8
TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1

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
