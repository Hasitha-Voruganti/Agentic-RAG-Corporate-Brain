"""
ingestion/pipeline.py — Full ingestion: parse → chunk → embed → store (Qdrant + ES)
"""
import uuid
from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    PointStruct, VectorParams, Distance, FieldCondition, MatchValue
)
from elasticsearch import AsyncElasticsearch

from core.config import get_settings
from core.embeddings import embedding_service
from core.database import AsyncSessionLocal, Document, DocumentChunk
from ingestion.parser import document_parser, text_splitter, ParsedChunk

settings = get_settings()


class IngestionPipeline:
    def __init__(self):
        self.qdrant = AsyncQdrantClient(url=settings.qdrant_url)
        self.es = AsyncElasticsearch(settings.es_url)

    async def initialize_stores(self):
        """Create Qdrant collection and ES index if not present."""
        # Qdrant
        collections = await self.qdrant.get_collections()
        names = [c.name for c in collections.collections]
        if settings.qdrant_collection not in names:
            await self.qdrant.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created Qdrant collection: {settings.qdrant_collection}")

        # Elasticsearch
        if not await self.es.indices.exists(index=settings.es_index):
            await self.es.indices.create(
                index=settings.es_index,
                body={
                    "mappings": {
                        "properties": {
                            "content": {"type": "text", "analyzer": "english"},
                            "document_id": {"type": "integer"},
                            "chunk_index": {"type": "integer"},
                            "allowed_roles": {"type": "keyword"},
                            "chunk_type": {"type": "keyword"},
                            "page_num": {"type": "integer"},
                        }
                    }
                }
            )
            logger.info(f"Created ES index: {settings.es_index}")

    async def ingest_document(self, document_id: int) -> int:
        """
        Full ingestion for a document_id already in DB.
        Returns the number of chunks created.
        """
        async with AsyncSessionLocal() as db:
            doc = await db.get(Document, document_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            doc.status = "processing"
            await db.commit()

            try:
                # 1. Parse
                raw_chunks = document_parser.parse(doc.file_path)
                logger.info(f"Parsed {len(raw_chunks)} raw chunks from {doc.filename}")

                # 2. Split
                split_chunks = text_splitter.split(raw_chunks)
                logger.info(f"Split into {len(split_chunks)} final chunks")

                # 3. Embed all at once
                texts = [c.content for c in split_chunks]
                vectors = await embedding_service.embed_batch(texts)

                # 4. Store
                qdrant_points = []
                es_actions = []
                db_chunks = []

                for i, (chunk, vector) in enumerate(zip(split_chunks, vectors)):
                    chunk_uuid = str(uuid.uuid4())

                    # Qdrant point
                    qdrant_points.append(PointStruct(
                        id=chunk_uuid,
                        vector=vector,
                        payload={
                            "document_id": document_id,
                            "chunk_index": i,
                            "content": chunk.content,
                            "allowed_roles": doc.allowed_roles,
                            "chunk_type": chunk.chunk_type,
                            "page_num": chunk.page_num,
                            "filename": doc.filename,
                            "title": doc.title,
                        }
                    ))

                    # Elasticsearch doc
                    es_actions.append({
                        "_index": settings.es_index,
                        "_id": chunk_uuid,
                        "_source": {
                            "content": chunk.content,
                            "document_id": document_id,
                            "chunk_index": i,
                            "allowed_roles": doc.allowed_roles,
                            "chunk_type": chunk.chunk_type,
                            "page_num": chunk.page_num,
                            "filename": doc.filename,
                            "title": doc.title,
                        }
                    })

                    # DB chunk record
                    db_chunks.append(DocumentChunk(
                        document_id=document_id,
                        chunk_index=i,
                        content=chunk.content,
                        metadata_=chunk.metadata,
                        qdrant_id=chunk_uuid
                    ))

                # Batch upsert to Qdrant
                await self.qdrant.upsert(
                    collection_name=settings.qdrant_collection,
                    points=qdrant_points
                )

                # Bulk index to ES (using helpers)
                from elasticsearch.helpers import async_bulk
                await async_bulk(self.es, es_actions)

                # Save chunks to DB
                db.add_all(db_chunks)
                doc.chunk_count = len(db_chunks)
                doc.status = "ready"
                await db.commit()

                logger.info(f"Ingested document {document_id}: {len(db_chunks)} chunks")
                return len(db_chunks)

            except Exception as e:
                doc.status = "failed"
                await db.commit()
                logger.error(f"Ingestion failed for doc {document_id}: {e}")
                raise

    async def delete_document(self, document_id: int):
        """Remove all chunks from Qdrant and ES for a document."""
        from qdrant_client.models import Filter
        await self.qdrant.delete(
            collection_name=settings.qdrant_collection,
            points_selector=Filter(
                must=[FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id)
                )]
            )
        )
        await self.es.delete_by_query(
            index=settings.es_index,
            body={"query": {"term": {"document_id": document_id}}}
        )
        logger.info(f"Deleted all chunks for document {document_id}")


ingestion_pipeline = IngestionPipeline()