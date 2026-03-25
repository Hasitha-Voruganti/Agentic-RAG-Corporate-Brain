"""
retrieval/hybrid.py — Hybrid search: Qdrant (semantic) + ES (keyword) → cross-encoder rerank
"""
import threading
from dataclasses import dataclass
from typing import Optional
import asyncio
from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny
from elasticsearch import AsyncElasticsearch
from sentence_transformers import CrossEncoder

from core.config import get_settings
from core.embeddings import embedding_service

settings = get_settings()

_cross_encoder: Optional[CrossEncoder] = None
_encoder_lock = threading.Lock()


def get_cross_encoder() -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        with _encoder_lock:
            if _cross_encoder is None:
                logger.info("Loading cross-encoder reranker...")
                _cross_encoder = CrossEncoder(
                    "cross-encoder/ms-marco-MiniLM-L-6-v2"
                )
                logger.info("Cross-encoder loaded successfully")
    return _cross_encoder


@dataclass
class RetrievedChunk:
    id: str
    content: str
    document_id: int
    filename: str
    title: str
    page_num: Optional[int]
    chunk_type: str
    score: float
    source: str  # "vector" | "keyword" | "hybrid"


class HybridRetriever:
    def __init__(self):
        self.qdrant = AsyncQdrantClient(url=settings.qdrant_url)
        self.es = AsyncElasticsearch(settings.es_url)

    async def search(
        self,
        query: str,
        user_roles: list[str],
        top_k: int = 5,
        filter_doc_ids: Optional[list[int]] = None
    ) -> list[RetrievedChunk]:
        """
        Full hybrid search pipeline:
        1. Vector search (Qdrant) + Keyword search (ES) — in parallel
        2. Reciprocal Rank Fusion
        3. Cross-encoder reranking
        """
        # Run both searches in parallel
        vector_results, keyword_results = await asyncio.gather(
            self._vector_search(
                query, user_roles,
                top_k=settings.top_k_vector,
                filter_doc_ids=filter_doc_ids
            ),
            self._keyword_search(
                query, user_roles,
                top_k=settings.top_k_keyword,
                filter_doc_ids=filter_doc_ids
            ),
        )

        # Fuse results
        fused = self._reciprocal_rank_fusion(vector_results, keyword_results)
        candidates = fused[:min(20, len(fused))]

        if not candidates:
            return []

        # Rerank
        reranked = self._rerank(query, candidates)
        return reranked[:top_k]

    async def _vector_search(
        self,
        query: str,
        user_roles: list[str],
        top_k: int = 15,
        filter_doc_ids: Optional[list[int]] = None
    ) -> list[RetrievedChunk]:
        try:
            query_vector = await embedding_service.embed_text(query)

            must_conditions = [
                FieldCondition(
                    key="allowed_roles",
                    match=MatchAny(any=user_roles)
                )
            ]
            if filter_doc_ids:
                must_conditions.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=filter_doc_ids)
                    )
                )

            results = await self.qdrant.search(
                collection_name=settings.qdrant_collection,
                query_vector=query_vector,
                query_filter=Filter(must=must_conditions),
                limit=top_k,
                with_payload=True
            )

            chunks = []
            for hit in results:
                p = hit.payload
                chunks.append(RetrievedChunk(
                    id=str(hit.id),
                    content=p["content"],
                    document_id=p["document_id"],
                    filename=p.get("filename", ""),
                    title=p.get("title", ""),
                    page_num=p.get("page_num"),
                    chunk_type=p.get("chunk_type", "text"),
                    score=hit.score,
                    source="vector"
                ))
            return chunks

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _keyword_search(
        self,
        query: str,
        user_roles: list[str],
        top_k: int = 15,
        filter_doc_ids: Optional[list[int]] = None
    ) -> list[RetrievedChunk]:
        try:
            must_filters = [{"terms": {"allowed_roles": user_roles}}]
            if filter_doc_ids:
                must_filters.append(
                    {"terms": {"document_id": filter_doc_ids}}
                )

            body = {
                "query": {
                    "bool": {
                        "must": [{
                            "multi_match": {
                                "query": query,
                                "fields": ["content^2", "title^1.5"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }],
                        "filter": must_filters
                    }
                },
                "size": top_k
            }

            resp = await self.es.search(
                index=settings.es_index, body=body
            )
            chunks = []
            for hit in resp["hits"]["hits"]:
                s = hit["_source"]
                chunks.append(RetrievedChunk(
                    id=hit["_id"],
                    content=s["content"],
                    document_id=s["document_id"],
                    filename=s.get("filename", ""),
                    title=s.get("title", ""),
                    page_num=s.get("page_num"),
                    chunk_type=s.get("chunk_type", "text"),
                    score=hit["_score"],
                    source="keyword"
                ))
            return chunks

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _reciprocal_rank_fusion(
        self,
        list1: list[RetrievedChunk],
        list2: list[RetrievedChunk],
        k: int = 60
    ) -> list[RetrievedChunk]:
        """Combine two ranked lists using RRF scoring."""
        scores: dict[str, float] = {}
        chunk_map: dict[str, RetrievedChunk] = {}

        for rank, chunk in enumerate(list1):
            scores[chunk.id] = scores.get(chunk.id, 0) + 1 / (k + rank + 1)
            chunk_map[chunk.id] = chunk

        for rank, chunk in enumerate(list2):
            scores[chunk.id] = scores.get(chunk.id, 0) + 1 / (k + rank + 1)
            if chunk.id not in chunk_map:
                chunk_map[chunk.id] = chunk

        sorted_ids = sorted(
            scores.keys(), key=lambda x: scores[x], reverse=True
        )
        result = []
        for cid in sorted_ids:
            c = chunk_map[cid]
            c.score = scores[cid]
            c.source = "hybrid"
            result.append(c)
        return result

    def _rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        """Cross-encoder reranking for precision."""
        if not chunks:
            return chunks
        try:
            encoder = get_cross_encoder()
            pairs = [(query, chunk.content) for chunk in chunks]
            scores = encoder.predict(pairs)
            for chunk, score in zip(chunks, scores):
                chunk.score = float(score)
            return sorted(chunks, key=lambda c: c.score, reverse=True)
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return chunks


hybrid_retriever = HybridRetriever()


# Pre-load cross-encoder in background thread
def _preload_cross_encoder():
    try:
        get_cross_encoder()
        logger.info("Cross-encoder pre-loaded and ready")
    except Exception as e:
        logger.warning(f"Cross-encoder pre-load failed: {e}")


threading.Thread(target=_preload_cross_encoder, daemon=True).start()