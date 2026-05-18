"""Abstract vector store repository interface for schema embeddings."""

from __future__ import annotations

from abc import ABC, abstractmethod

from text_to_sql_agent.models import SchemaEmbeddingRecord


class VectorStoreRepository(ABC):
    """Abstract base class for vector-backed schema embedding storage."""

    @abstractmethod
    def upsert_documents(
        self,
        records: list[SchemaEmbeddingRecord],
    ) -> list[str]:
        """Insert or update embedded records and return their embedding IDs."""

    @abstractmethod
    def search_similar(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        database_id: str | None = None,
        snapshot_id: str | None = None,
    ) -> list[SchemaEmbeddingRecord]:
        """Search for similar records using a query vector and optional filters."""

    @abstractmethod
    def delete_by_snapshot(self, snapshot_id: str) -> int:
        """Delete all indexed records for a snapshot and return the count removed."""