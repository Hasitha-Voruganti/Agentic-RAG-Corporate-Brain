"""
api/main.py — FastAPI application with all routes
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.config import get_settings
from core.database import create_tables, get_db, User, Document, DocumentChunk, QueryLog
from security.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_accessible_roles, require_role
)
from ingestion.pipeline import ingestion_pipeline
from agents.rag_agent import rag_agent

settings = get_settings()

app = FastAPI(
    title="Corporate Brain API",
    description="Agentic RAG-based Enterprise Knowledge System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supported file types
SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".txt", ".pptx"]


# ── Startup ────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await create_tables()
    await ingestion_pipeline.initialize_stores()
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info("Corporate Brain API started successfully")


# ── Pydantic Schemas ────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "general"


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


class QueryRequest(BaseModel):
    query: str
    filter_doc_ids: Optional[list[int]] = None


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    sources: list[dict]
    iterations: int
    rewrite_history: list[str]
    reasoning: str


class DocumentOut(BaseModel):
    id: int
    title: str
    filename: str
    file_type: str
    allowed_roles: list
    status: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DeleteResponse(BaseModel):
    message: str


# ── Auth Routes ─────────────────────────────────────────────────────────────
@app.post("/api/auth/register", response_model=UserOut, tags=["Auth"])
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if username already exists
    existing = await db.execute(
        select(User).where(User.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Username already registered")

    # Check if email already exists
    existing_email = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    valid_roles = ["admin", "hr", "finance", "general"]
    if body.role not in valid_roles:
        raise HTTPException(
            400, f"Invalid role. Must be one of: {valid_roles}"
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"New user registered: {user.username} ({user.role})")
    return user


@app.post("/api/auth/login", response_model=Token, tags=["Auth"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid username or password")

    if not user.is_active:
        raise HTTPException(403, "Account is deactivated. Contact admin.")

    token = create_access_token({"sub": user.username, "role": user.role})
    logger.info(f"User logged in: {user.username}")
    return Token(access_token=token, token_type="bearer", user=user)


@app.get("/api/auth/me", response_model=UserOut, tags=["Auth"])
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/api/auth/users", response_model=list[UserOut], tags=["Auth"])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """List all users — admin only"""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@app.delete("/api/auth/users/{user_id}", tags=["Auth"])
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Delete a user — admin only"""
    if user_id == current_user.id:
        raise HTTPException(400, "Cannot delete your own account")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    await db.delete(user)
    await db.commit()
    return {"message": f"User '{user.username}' deleted"}


# ── Document Routes ─────────────────────────────────────────────────────────
@app.post("/api/documents/upload", response_model=DocumentOut, tags=["Documents"])
async def upload_document(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    allowed_roles: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "hr", "finance"))
):
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Validate roles
    valid_roles = ["admin", "hr", "finance", "general"]
    roles = [r.strip() for r in allowed_roles.split(",") if r.strip()]
    invalid = [r for r in roles if r not in valid_roles]
    if invalid:
        raise HTTPException(
            400,
            f"Invalid roles: {invalid}. Valid roles: {valid_roles}"
        )
    if not roles:
        raise HTTPException(400, "At least one role must be specified")

    # Save file to disk
    dest_dir = Path(settings.upload_dir) / str(current_user.id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Handle duplicate filenames by adding timestamp
    safe_filename = f"{Path(file.filename).stem}_{int(datetime.utcnow().timestamp())}{ext}"
    dest_path = str(dest_dir / safe_filename)

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(dest_path)
    logger.info(
        f"File saved: {safe_filename} "
        f"({file_size / 1024:.1f} KB) by {current_user.username}"
    )

    # Create document record
    doc = Document(
        title=title,
        filename=file.filename,
        file_type=ext.lstrip("."),
        file_path=dest_path,
        allowed_roles=roles,
        uploader_id=current_user.id,
        status="pending"
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Kick off ingestion in background
    background_tasks.add_task(ingestion_pipeline.ingest_document, doc.id)
    logger.info(f"Document {doc.id} queued for ingestion")

    return doc


@app.get("/api/documents", response_model=list[DocumentOut], tags=["Documents"])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all documents accessible to the current user's role"""
    accessible_roles = get_accessible_roles(current_user.role)
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()

    # Filter by RBAC — only return docs the user's role can access
    return [
        doc for doc in docs
        if any(role in accessible_roles for role in doc.allowed_roles)
    ]


@app.get("/api/documents/{doc_id}", response_model=DocumentOut, tags=["Documents"])
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single document by ID"""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    accessible_roles = get_accessible_roles(current_user.role)
    if not any(role in accessible_roles for role in doc.allowed_roles):
        raise HTTPException(403, "You do not have access to this document")

    return doc


@app.delete("/api/documents/{doc_id}", response_model=DeleteResponse, tags=["Documents"])
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Delete a document and all its chunks — admin only"""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    doc_title = doc.title

    # Step 1 — Remove from vector stores (Qdrant + Elasticsearch)
    try:
        await ingestion_pipeline.delete_document(doc_id)
        logger.info(f"Deleted doc {doc_id} from vector stores")
    except Exception as e:
        logger.warning(f"Vector store cleanup warning for doc {doc_id}: {e}")

    # Step 2 — Remove chunks from Postgres (foreign key must go first)
    try:
        await db.execute(
            text("DELETE FROM document_chunks WHERE document_id = :doc_id"),
            {"doc_id": doc_id}
        )
        await db.commit()
        logger.info(f"Deleted chunks for doc {doc_id} from database")
    except Exception as e:
        logger.error(f"Failed to delete chunks for doc {doc_id}: {e}")
        raise HTTPException(500, f"Failed to delete document chunks: {str(e)}")

    # Step 3 — Remove document record
    try:
        doc = await db.get(Document, doc_id)
        if doc:
            await db.delete(doc)
            await db.commit()
        logger.info(f"Deleted document record {doc_id}")
    except Exception as e:
        logger.error(f"Failed to delete document record {doc_id}: {e}")
        raise HTTPException(500, f"Failed to delete document: {str(e)}")

    # Step 4 — Remove file from disk
    try:
        if doc and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
            logger.info(f"Deleted file from disk: {doc.file_path}")
    except Exception as e:
        logger.warning(f"Could not delete file from disk: {e}")

    return DeleteResponse(message=f"Document '{doc_title}' deleted successfully")


# ── Query Routes ─────────────────────────────────────────────────────────────
@app.post("/api/query", response_model=QueryResponse, tags=["Query"])
async def query(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run an agentic RAG query against the knowledge base"""
    if not body.query or not body.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    user_roles = get_accessible_roles(current_user.role)
    logger.info(
        f"Query from {current_user.username} ({current_user.role}): "
        f"{body.query[:80]}"
    )

    state = await rag_agent.run(
        query=body.query.strip(),
        user_roles=user_roles
    )

    sources = [
        {
            "id": chunk.id,
            "title": chunk.title,
            "filename": chunk.filename,
            "page_num": chunk.page_num,
            "chunk_type": chunk.chunk_type,
            "score": round(chunk.score, 4),
            "excerpt": (
                chunk.content[:300] + "..."
                if len(chunk.content) > 300
                else chunk.content
            )
        }
        for chunk in state.retrieved_chunks
    ]

    # Save query to history
    log = QueryLog(
        user_id=current_user.id,
        query=state.original_query,
        rewritten_query=(
            state.current_query
            if state.current_query != state.original_query
            else None
        ),
        answer=state.answer,
        sources=[s["filename"] for s in sources],
        confidence=state.confidence,
        iterations=state.iterations
    )
    db.add(log)
    await db.commit()

    return QueryResponse(
        answer=state.answer,
        confidence=round(state.confidence, 3),
        sources=sources,
        iterations=state.iterations,
        rewrite_history=state.rewrite_history,
        reasoning=state.reasoning
    )


@app.get("/api/query/history", tags=["Query"])
async def query_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the last 50 queries for the current user"""
    result = await db.execute(
        select(QueryLog)
        .where(QueryLog.user_id == current_user.id)
        .order_by(QueryLog.created_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "query": log.query,
            "rewritten_query": log.rewritten_query,
            "answer": log.answer,
            "confidence": log.confidence,
            "iterations": log.iterations,
            "sources": log.sources,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]


@app.delete("/api/query/history", tags=["Query"])
async def clear_query_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear query history for the current user"""
    await db.execute(
        text("DELETE FROM query_logs WHERE user_id = :uid"),
        {"uid": current_user.id}
    )
    await db.commit()
    return {"message": "Query history cleared"}


# ── System Routes ─────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Corporate Brain API is running",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }


@app.get("/health", tags=["System"])
async def health(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "database": db_status,
        "supported_file_types": SUPPORTED_EXTENSIONS
    }