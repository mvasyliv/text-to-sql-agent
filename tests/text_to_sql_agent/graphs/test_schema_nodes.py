"""Tests for LangGraph schema ingestion node functions (T-2026-05-15-033)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from text_to_sql_agent.graphs import (
    build_schema_documents,
    index_schema_embeddings,
    introspect_schema,
    load_connection_context,
    normalize_schema,
    persist_schema_snapshot,
)
from text_to_sql_agent.graphs.state import SchemaReadState
from text_to_sql_agent.models import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeySchema,
    RawColumnMeta,
    RawForeignKeyMeta,
    RawIntrospectionResult,
    RawTableMeta,
    SchemaDocument,
    SchemaEmbeddingRecord,
    TableSchema,
)
from text_to_sql_agent.repositories import (
    SchemaIntrospectionProvider,
    SchemaSnapshotRepository,
    VectorStoreRepository,
)


def _base_state() -> SchemaReadState:
    return {
        "request_id": "req-001",
        "database_id": "warehouse",
        "dialect": None,
        "refresh_mode": "full",
        "target_tables": None,
        "force_refresh": False,
        "connection_config_ref": "env:DATABASE_URL",
        "introspection_result": None,
        "normalized_schema": None,
        "snapshot_id": None,
        "document_ids": [],
        "embedding_ids": [],
        "status": "pending",
        "current_node": None,
        "retry_count": 0,
        "errors": [],
        "warnings": [],
        "introspected_at": None,
        "completed_at": None,
    }


def _raw_result() -> RawIntrospectionResult:
    return RawIntrospectionResult(
        database_id="warehouse",
        dialect="postgresql",
        introspected_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            RawTableMeta(
                name="orders",
                table_type="BASE TABLE",
                schema_name="public",
                columns=[
                    RawColumnMeta(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                        is_unique=True,
                        ordinal_position=1,
                    ),
                    RawColumnMeta(
                        name="customer_id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=False,
                        is_unique=False,
                        ordinal_position=2,
                    ),
                ],
                foreign_keys=[
                    RawForeignKeyMeta(
                        constraint_name="fk_orders_customer",
                        from_table="orders",
                        from_column="customer_id",
                        to_table="customers",
                        to_column="id",
                    )
                ],
            )
        ],
    )


class StubIntrospectionProvider(SchemaIntrospectionProvider):
    def introspect(self, database_id: str, connection_config: dict[str, object]) -> RawIntrospectionResult:
        return _raw_result()


class RecordingVectorStoreRepository(VectorStoreRepository):
    def __init__(self) -> None:
        self.records: list[SchemaEmbeddingRecord] = []

    def upsert_documents(self, records: list[SchemaEmbeddingRecord]) -> list[str]:
        self.records.extend(records)
        return [record.embedding_id for record in records]

    def search_similar(self, query_vector: list[float], *, limit: int = 10, database_id: str | None = None, snapshot_id: str | None = None) -> list[SchemaEmbeddingRecord]:
        return []

    def delete_by_snapshot(self, snapshot_id: str) -> int:
        return 0


def test_load_connection_context_validates_reference() -> None:
    state = _base_state()

    update = load_connection_context(
        state,
        lambda ref: {"dialect": "postgresql", "host": "localhost"},
    )

    assert update["current_node"] == "load_connection_context"
    assert update["dialect"] == "postgresql"
    assert update["warnings"] == []


def test_introspect_schema_uses_provider_factory_and_connection_resolver() -> None:
    state = _base_state()

    update = introspect_schema(
        state,
        lambda ref: {"dialect": "postgresql", "host": "localhost"},
        provider_factory=lambda dialect: StubIntrospectionProvider(),
    )

    assert update["current_node"] == "introspect_schema"
    assert update["status"] == "introspecting"
    assert update["dialect"] == "postgresql"
    assert update["introspection_result"].database_id == "warehouse"


def test_normalize_schema_sets_normalized_schema() -> None:
    state = _base_state()
    state["introspection_result"] = _raw_result()

    update = normalize_schema(state)

    assert update["current_node"] == "normalize_schema"
    assert update["status"] == "normalizing"
    assert update["normalized_schema"].snapshot_id == "warehouse-20260515T120000Z"


def test_build_schema_documents_node_returns_document_ids() -> None:
    state = _base_state()
    state["normalized_schema"] = DatabaseSchema(
        database_id="warehouse",
        dialect="postgresql",
        snapshot_id="warehouse-20260515T120000Z",
        created_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            TableSchema(
                name="orders",
                table_type="TABLE",
                columns=[
                    ColumnSchema(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                        is_foreign_key=False,
                        ordinal_position=1,
                    ),
                    ColumnSchema(
                        name="customer_id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=False,
                        is_foreign_key=True,
                        ordinal_position=2,
                    ),
                ],
                foreign_keys=[
                    ForeignKeySchema(
                        from_column="customer_id",
                        to_table="customers",
                        to_column="id",
                    )
                ],
                primary_keys=["id"],
            )
        ],
    )

    update = build_schema_documents(state)

    assert update["current_node"] == "build_schema_documents"
    assert update["status"] == "persisting"
    assert len(update["document_ids"]) == 3


def test_persist_schema_snapshot_persists_normalized_schema(tmp_path: Path) -> None:
    state = _base_state()
    state["normalized_schema"] = DatabaseSchema(
        database_id="warehouse",
        dialect="postgresql",
        snapshot_id="warehouse-20260515T120000Z",
        created_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[],
    )
    repository = SchemaSnapshotRepository(tmp_path / "snapshots")

    update = persist_schema_snapshot(state, repository)

    assert update["current_node"] == "persist_schema_snapshot"
    assert update["status"] == "persisting"
    assert update["snapshot_id"] == "warehouse-20260515T120000Z"
    assert repository.load("warehouse-20260515T120000Z") == state["normalized_schema"]


def test_index_schema_embeddings_node_returns_embeddings_and_document_ids() -> None:
    state = _base_state()
    state["normalized_schema"] = DatabaseSchema(
        database_id="warehouse",
        dialect="postgresql",
        snapshot_id="warehouse-20260515T120000Z",
        created_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            TableSchema(
                name="orders",
                table_type="TABLE",
                columns=[
                    ColumnSchema(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                        is_foreign_key=False,
                        ordinal_position=1,
                    )
                ],
                primary_keys=["id"],
            )
        ],
    )
    repository = RecordingVectorStoreRepository()

    update = index_schema_embeddings(
        state,
        repository,
        lambda content: [float(len(content))],
        indexed_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert update["current_node"] == "index_schema_embeddings"
    assert update["status"] == "indexing"
    assert len(update["document_ids"]) == 2
    assert len(update["embedding_ids"]) == 2