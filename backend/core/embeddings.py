"""
core/embeddings.py — Local HuggingFace embeddings with background pre-loading
"""
import threading
from sentence_transformers import SentenceTransformer
from loguru import logger
from core.config import get_settings

settings = get_settings()

_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info(f"Loading embedding model: {settings.embedding_model}")
                _model = SentenceTransformer(settings.embedding_model)
                logger.info("Embedding model loaded successfully")
    return _model


class EmbeddingService:
    def __init__(self):
        self.dim = settings.embedding_dim

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string locally."""
        model = get_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts locally."""
        logger.info(f"Embedding {len(texts)} texts locally")
        model = get_model()
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32
        )
        return [v.tolist() for v in vectors]


embedding_service = EmbeddingService()


# Pre-load model in background thread so first query is instant
def _preload_embedding_model():
    try:
        get_model()
        logger.info("Embedding model pre-loaded and ready")
    except Exception as e:
        logger.warning(f"Embedding model pre-load failed: {e}")


threading.Thread(target=_preload_embedding_model, daemon=True).start()