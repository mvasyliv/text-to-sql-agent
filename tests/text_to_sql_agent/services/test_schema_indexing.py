"""Tests for schema indexing service (T-2026-05-15-032)."""

from datetime import datetime, timezone
from typing import Any

from text_to_sql_agent.models import SchemaDocument, SchemaEmbeddingRecord
from text_to_sql_agent.repositories import VectorStoreRepository
from text_to_sql_agent.services import index_schema_embeddings


class RecordingVectorStoreRepository(VectorStoreRepository):
    """In-memory vector store spy for indexing tests."""

    def __init__(self) -> None:
        self.records: list[SchemaEmbeddingRecord] = []

    def upsert_documents(self, records: list[SchemaEmbeddingRecord]) -> list[str]:
        self.records.extend(records)
        return [record.embedding_id for record in records]

    def search_similar(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        database_id: str | None = None,
        snapshot_id: str | None = None,
    ) -> list[SchemaEmbeddingRecord]:
        return []

    def delete_by_snapshot(self, snapshot_id: str) -> int:
        return 0


def _document(
    doc_id: str,
    *,
    content: str = "Table orders contains customer purchase records.",
) -> SchemaDocument:
    return SchemaDocument(
        doc_id=doc_id,
        database_id="warehouse",
        snapshot_id="snapshot-1",
        granularity="table",
        table_name="orders",
        column_names=["id", "customer_id"],
        content=content,
        domain_tags=["sales"],
        metadata={"table_type": "TABLE"},
    )


def test_index_schema_embeddings_returns_embedding_ids() -> None:
    """Indexing should return the IDs returned by the vector store."""
    repository = RecordingVectorStoreRepository()

    result = index_schema_embeddings(
        [_document("doc-1"), _document("doc-2")],
        repository,
        lambda content: [float(len(content))],
        embedding_id_factory=lambda document: f"emb-{document.doc_id}",
        indexed_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert result == ["emb-doc-1", "emb-doc-2"]


def test_index_schema_embeddings_persists_embedding_records() -> None:
    """The service should materialize schema embedding records before persisting."""
    repository = RecordingVectorStoreRepository()

    index_schema_embeddings(
        [_document("doc-1", content="One two three")],
        repository,
        lambda content: [float(len(content)), 0.5],
        embedding_id_factory=lambda document: f"emb-{document.doc_id}",
        indexed_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert len(repository.records) == 1
    record = repository.records[0]
    assert record.embedding_id == "emb-doc-1"
    assert record.doc_id == "doc-1"
    assert record.database_id == "warehouse"
    assert record.snapshot_id == "snapshot-1"
    assert record.vector == [13.0, 0.5]
    assert record.indexed_at == datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_index_schema_embeddings_calls_embedder_once_per_document() -> None:
    """Each document should be embedded independently."""
    repository = RecordingVectorStoreRepository()
    calls: list[str] = []

    def embedder(content: str) -> list[float]:
        calls.append(content)
        return [float(len(content))]

    index_schema_embeddings(
        [_document("doc-1", content="alpha"), _document("doc-2", content="beta")],
        repository,
        embedder,
        embedding_id_factory=lambda document: f"emb-{document.doc_id}",
        indexed_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert calls == ["alpha", "beta"]


def test_index_schema_embeddings_uses_default_embedding_id_factory() -> None:
    """Default embedding IDs should be stable and non-empty."""
    repository = RecordingVectorStoreRepository()

    result = index_schema_embeddings(
        [_document("doc-1")],
        repository,
        lambda content: [1.0],
        indexed_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert len(result[0]) > 0
    assert repository.records[0].embedding_id == result[0]


def test_index_schema_embeddings_returns_empty_for_no_documents() -> None:
    """No documents should short-circuit without touching the repository."""
    repository = RecordingVectorStoreRepository()
    calls: list[str] = []

    result = index_schema_embeddings(
        [],
        repository,
        lambda content: calls.append(content) or [1.0],
    )

    assert result == []
    assert calls == []
    assert repository.records == []