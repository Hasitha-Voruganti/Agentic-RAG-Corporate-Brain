"""
core/config.py — Centralized settings via pydantic-settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    # LLM — Groq (free)
    groq_api_key: str
    llm_model: str = "llama-3.1-8b-instant"

    # Embeddings — local HuggingFace (free, runs on your machine)
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Databases
    database_url: str = "postgresql+asyncpg://brain:brain_secret@localhost:5432/corporate_brain"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "corporate_docs"
    es_url: str = "http://localhost:9200"
    es_index: str = "corporate_docs"
    redis_url: str = "redis://localhost:6379"

    # Auth
    jwt_secret: str = "mysupersecretkey123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Retrieval — reduced candidate count for faster reranking
    # top_k_vector: int = 15
    # top_k_keyword: int = 15
    # top_k_rerank: int = 5
    # self_reflection_threshold: float = 0.55
    top_k_vector: int = 20
    top_k_keyword: int = 20
    top_k_rerank: int = 8
    # Ingestion
    chunk_size: int = 512
    chunk_overlap: int = 64
    upload_dir: str = "./uploads"

    # Agent
    max_agent_iterations: int = 5
    self_reflection_threshold: float = 0.65

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()