"""Tests for abstract VectorStoreRepository interface (T-2026-05-15-031)."""

from datetime import datetime, timezone
from typing import Any

import pytest

from text_to_sql_agent.models import SchemaEmbeddingRecord
from text_to_sql_agent.repositories import VectorStoreRepository


class MockVectorStoreRepository(VectorStoreRepository):
    """Concrete in-memory mock for exercising the abstract contract."""

    def __init__(self) -> None:
        self._records: list[SchemaEmbeddingRecord] = []

    def upsert_documents(self, records: list[SchemaEmbeddingRecord]) -> list[str]:
        embedding_ids = [record.embedding_id for record in records]
        self._records.extend(records)
        return embedding_ids

    def search_similar(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        database_id: str | None = None,
        snapshot_id: str | None = None,
    ) -> list[SchemaEmbeddingRecord]:
        matching = [
            record
            for record in self._records
            if (database_id is None or record.database_id == database_id)
            and (snapshot_id is None or record.snapshot_id == snapshot_id)
        ]
        return matching[:limit]

    def delete_by_snapshot(self, snapshot_id: str) -> int:
        before_count = len(self._records)
        self._records = [record for record in self._records if record.snapshot_id != snapshot_id]
        return before_count - len(self._records)


def _embedding_record(
    embedding_id: str,
    *,
    database_id: str = "warehouse",
    snapshot_id: str = "snapshot-a",
    vector: list[float] | None = None,
) -> SchemaEmbeddingRecord:
    return SchemaEmbeddingRecord(
        embedding_id=embedding_id,
        doc_id=f"doc-{embedding_id}",
        database_id=database_id,
        snapshot_id=snapshot_id,
        vector=vector or [0.1, 0.2, 0.3],
        indexed_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_vector_store_repository_cannot_instantiate_directly() -> None:
    """Abstract base class should not be instantiable."""
    with pytest.raises(TypeError) as exc_info:
        VectorStoreRepository()  # type: ignore[abstract]

    assert "abstract" in str(exc_info.value).lower()


def test_vector_store_repository_requires_all_methods() -> None:
    """Incomplete subclasses should remain abstract."""

    class IncompleteVectorStoreRepository(VectorStoreRepository):
        def upsert_documents(self, records: list[SchemaEmbeddingRecord]) -> list[str]:
            return [record.embedding_id for record in records]

    with pytest.raises(TypeError):
        IncompleteVectorStoreRepository()  # type: ignore[abstract]


def test_mock_vector_store_repository_upsert_returns_embedding_ids() -> None:
    """Upsert should return the IDs of persisted embedding records."""
    repository = MockVectorStoreRepository()
    records = [_embedding_record("emb-1"), _embedding_record("emb-2")]

    result = repository.upsert_documents(records)

    assert result == ["emb-1", "emb-2"]


def test_mock_vector_store_repository_search_filters_by_database_and_snapshot() -> None:
    """Search should respect optional database and snapshot filters."""
    repository = MockVectorStoreRepository()
    repository.upsert_documents(
        [
            _embedding_record("emb-1", database_id="warehouse", snapshot_id="snapshot-a"),
            _embedding_record("emb-2", database_id="warehouse", snapshot_id="snapshot-b"),
            _embedding_record("emb-3", database_id="analytics", snapshot_id="snapshot-a"),
        ]
    )

    results = repository.search_similar(
        [0.1, 0.2, 0.3],
        database_id="warehouse",
        snapshot_id="snapshot-a",
    )

    assert [record.embedding_id for record in results] == ["emb-1"]


def test_mock_vector_store_repository_search_applies_limit() -> None:
    """Search should cap the number of returned records."""
    repository = MockVectorStoreRepository()
    repository.upsert_documents([
        _embedding_record("emb-1"),
        _embedding_record("emb-2"),
        _embedding_record("emb-3"),
    ])

    results = repository.search_similar([0.1, 0.2, 0.3], limit=2)

    assert len(results) == 2


def test_mock_vector_store_repository_delete_by_snapshot_returns_count() -> None:
    """Delete should return the number of removed records."""
    repository = MockVectorStoreRepository()
    repository.upsert_documents(
        [
            _embedding_record("emb-1", snapshot_id="snapshot-a"),
            _embedding_record("emb-2", snapshot_id="snapshot-a"),
            _embedding_record("emb-3", snapshot_id="snapshot-b"),
        ]
    )

    removed = repository.delete_by_snapshot("snapshot-a")

    assert removed == 2
    assert [record.embedding_id for record in repository.search_similar([0.1], limit=10)] == ["emb-3"]


def test_mock_vector_store_repository_supports_empty_results() -> None:
    """Search and delete should handle empty repositories cleanly."""
    repository = MockVectorStoreRepository()

    assert repository.search_similar([0.1, 0.2]) == []
    assert repository.delete_by_snapshot("missing") == 0