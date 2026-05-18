"""Schema indexing service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid5, NAMESPACE_URL

from text_to_sql_agent.models import SchemaDocument, SchemaEmbeddingRecord
from text_to_sql_agent.repositories import VectorStoreRepository

EmbeddingFunction = Callable[[str], list[float]]
EmbeddingIdFactory = Callable[[SchemaDocument], str]


def index_schema_embeddings(
    documents: list[SchemaDocument],
    vector_store: VectorStoreRepository,
    embedder: EmbeddingFunction,
    *,
    embedding_id_factory: EmbeddingIdFactory | None = None,
    indexed_at: datetime | None = None,
) -> list[str]:
    """Generate embeddings for schema documents and persist them to a vector store."""
    if not documents:
        return []

    resolved_indexed_at = indexed_at or datetime.now(timezone.utc)
    resolved_id_factory = embedding_id_factory or _default_embedding_id_factory

    records = [
        SchemaEmbeddingRecord(
            embedding_id=resolved_id_factory(document),
            doc_id=document.doc_id,
            database_id=document.database_id,
            snapshot_id=document.snapshot_id,
            vector=embedder(document.content),
            indexed_at=resolved_indexed_at,
        )
        for document in documents
    ]

    return vector_store.upsert_documents(records)


def _default_embedding_id_factory(document: SchemaDocument) -> str:
    """Build a stable embedding ID for a document."""
    return str(uuid5(NAMESPACE_URL, f"{document.snapshot_id}:{document.doc_id}"))