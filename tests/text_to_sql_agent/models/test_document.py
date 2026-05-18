"""Tests for document and embedding Pydantic models (T-2026-05-15-021)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from text_to_sql_agent.models.document import (
    SchemaDocument,
    SchemaEmbeddingRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# SchemaDocument
# ---------------------------------------------------------------------------


def test_schema_document_required_fields() -> None:
    doc = SchemaDocument(
        doc_id="doc-001",
        database_id="db-001",
        snapshot_id="snap-abc",
        granularity="table",
        table_name="orders",
        content="Table orders contains customer purchase records.",
    )
    assert doc.doc_id == "doc-001"
    assert doc.granularity == "table"
    assert doc.table_name == "orders"
    assert doc.column_names == []
    assert doc.domain_tags == []
    assert doc.metadata == {}


def test_schema_document_with_all_fields() -> None:
    doc = SchemaDocument(
        doc_id="doc-002",
        database_id="db-002",
        snapshot_id="snap-xyz",
        granularity="column_group",
        table_name="employees",
        column_names=["id", "name", "salary"],
        content="Columns: id (PK), name (VARCHAR), salary (DECIMAL).",
        domain_tags=["hr", "finance"],
        metadata={"owner": "hr-team", "sensitive": "true"},
    )
    assert len(doc.column_names) == 3
    assert doc.column_names[0] == "id"
    assert len(doc.domain_tags) == 2
    assert doc.metadata["owner"] == "hr-team"


def test_schema_document_granularity_values() -> None:
    for granularity_value in ["table", "column_group", "relationship"]:
        doc = SchemaDocument(
            doc_id="doc-x",
            database_id="db-x",
            snapshot_id="snap-x",
            granularity=granularity_value,
            table_name="x",
            content="x",
        )
        assert doc.granularity == granularity_value


def test_schema_document_missing_required_raises() -> None:
    with pytest.raises(ValidationError):
        SchemaDocument(
            doc_id="doc-x",
            database_id="db-x",
            snapshot_id="snap-x",
            table_name="x",
            # Missing required: granularity, content
        )  # type: ignore[call-arg]


def test_schema_document_empty_metadata() -> None:
    doc = SchemaDocument(
        doc_id="doc-003",
        database_id="db-003",
        snapshot_id="snap-003",
        granularity="table",
        table_name="products",
        content="Products table.",
        metadata={},
    )
    assert doc.metadata == {}


def test_schema_document_serialization_roundtrip() -> None:
    doc = SchemaDocument(
        doc_id="doc-004",
        database_id="db-004",
        snapshot_id="snap-004",
        granularity="relationship",
        table_name="orders",
        column_names=["customer_id"],
        content="FK relationship: orders.customer_id → customers.id",
        domain_tags=["sales"],
        metadata={"relation_type": "many-to-one"},
    )
    dumped = doc.model_dump()
    restored = SchemaDocument.model_validate(dumped)
    assert restored.doc_id == "doc-004"
    assert restored.granularity == "relationship"
    assert restored.column_names == ["customer_id"]
    assert restored.metadata["relation_type"] == "many-to-one"


# ---------------------------------------------------------------------------
# SchemaEmbeddingRecord
# ---------------------------------------------------------------------------


def test_schema_embedding_record_required_fields() -> None:
    embedding = SchemaEmbeddingRecord(
        embedding_id="emb-001",
        doc_id="doc-001",
        database_id="db-001",
        snapshot_id="snap-abc",
        vector=[0.1, 0.2, 0.3],
        indexed_at=_now(),
    )
    assert embedding.embedding_id == "emb-001"
    assert embedding.doc_id == "doc-001"
    assert len(embedding.vector) == 3
    assert embedding.vector[0] == 0.1


def test_schema_embedding_record_large_vector() -> None:
    # Simulate a typical OpenAI embedding (1536 dimensions)
    large_vector = [0.1] * 1536
    embedding = SchemaEmbeddingRecord(
        embedding_id="emb-002",
        doc_id="doc-002",
        database_id="db-002",
        snapshot_id="snap-002",
        vector=large_vector,
        indexed_at=_now(),
    )
    assert len(embedding.vector) == 1536
    assert embedding.vector[0] == 0.1
    assert embedding.vector[-1] == 0.1


def test_schema_embedding_record_zero_vector() -> None:
    """Edge case: zero vector (should be allowed for consistency)."""
    embedding = SchemaEmbeddingRecord(
        embedding_id="emb-003",
        doc_id="doc-003",
        database_id="db-003",
        snapshot_id="snap-003",
        vector=[],
        indexed_at=_now(),
    )
    assert embedding.vector == []


def test_schema_embedding_record_missing_required_raises() -> None:
    with pytest.raises(ValidationError):
        SchemaEmbeddingRecord(
            embedding_id="emb-x",
            doc_id="doc-x",
            database_id="db-x",
            snapshot_id="snap-x",
            # Missing required: vector, indexed_at
        )  # type: ignore[call-arg]


def test_schema_embedding_record_serialization_roundtrip() -> None:
    vector = [0.1, 0.2, 0.3, 0.4, 0.5]
    indexed_at = _now()
    embedding = SchemaEmbeddingRecord(
        embedding_id="emb-004",
        doc_id="doc-004",
        database_id="db-004",
        snapshot_id="snap-004",
        vector=vector,
        indexed_at=indexed_at,
    )
    dumped = embedding.model_dump()
    restored = SchemaEmbeddingRecord.model_validate(dumped)
    assert restored.embedding_id == "emb-004"
    assert restored.vector == vector
    # Note: datetime serialization may round microseconds, so compare with tolerance
    assert abs((restored.indexed_at - indexed_at).total_seconds()) < 1.0


def test_schema_embedding_record_datetime_precision() -> None:
    """Test that datetime is preserved during serialization."""
    now_precise = datetime(2026, 5, 15, 12, 30, 45, 123456, tzinfo=timezone.utc)
    embedding = SchemaEmbeddingRecord(
        embedding_id="emb-005",
        doc_id="doc-005",
        database_id="db-005",
        snapshot_id="snap-005",
        vector=[0.1],
        indexed_at=now_precise,
    )
    dumped = embedding.model_dump()
    restored = SchemaEmbeddingRecord.model_validate(dumped)
    assert restored.indexed_at == now_precise


# ---------------------------------------------------------------------------
# Integration: Document + Embedding pair
# ---------------------------------------------------------------------------


def test_document_embedding_pair_consistency() -> None:
    """Verify that a SchemaDocument and SchemaEmbeddingRecord can be paired."""
    doc = SchemaDocument(
        doc_id="doc-pair-001",
        database_id="db-pair",
        snapshot_id="snap-pair",
        granularity="table",
        table_name="users",
        content="Users table with id, email, created_at.",
        domain_tags=["core"],
    )
    embedding = SchemaEmbeddingRecord(
        embedding_id="emb-pair-001",
        doc_id=doc.doc_id,  # Link back to document
        database_id=doc.database_id,
        snapshot_id=doc.snapshot_id,
        vector=[0.5] * 10,
        indexed_at=_now(),
    )
    # Verify cross-references
    assert embedding.doc_id == doc.doc_id
    assert embedding.database_id == doc.database_id
    assert embedding.snapshot_id == doc.snapshot_id
