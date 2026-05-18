"""Tests for the compiled schema ingestion graph."""

from datetime import datetime, timezone

from text_to_sql_agent.graphs import build_schema_ingestion_graph
from text_to_sql_agent.models import (
    RawColumnMeta,
    RawForeignKeyMeta,
    RawIntrospectionResult,
    RawTableMeta,
)
from text_to_sql_agent.repositories import SchemaIntrospectionProvider, SchemaSnapshotRepository, VectorStoreRepository


def _initial_state() -> dict[str, object]:
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


class _StaticIntrospectionProvider(SchemaIntrospectionProvider):
    def introspect(self, database_id: str, connection_config: dict[str, object]) -> RawIntrospectionResult:
        return _raw_result()


class _FlakyIntrospectionProvider(SchemaIntrospectionProvider):
    def __init__(self) -> None:
        self.calls = 0

    def introspect(self, database_id: str, connection_config: dict[str, object]) -> RawIntrospectionResult:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary schema load failure")
        return _raw_result()


class _RecordingVectorStoreRepository(VectorStoreRepository):
    def __init__(self) -> None:
        self.records = []

    def upsert_documents(self, records):
        self.records.extend(records)
        return [record.embedding_id for record in records]

    def search_similar(self, query_vector, *, limit=10, database_id=None, snapshot_id=None):
        return []

    def delete_by_snapshot(self, snapshot_id):
        return 0


def test_schema_ingestion_graph_completes_successfully(tmp_path) -> None:
    snapshot_repository = SchemaSnapshotRepository(tmp_path / "snapshots")
    vector_store = _RecordingVectorStoreRepository()
    provider = _StaticIntrospectionProvider()
    graph = build_schema_ingestion_graph(
        lambda ref: {"dialect": "postgresql", "host": "localhost"},
        snapshot_repository,
        vector_store,
        lambda content: [float(len(content))],
        provider_factory=lambda dialect: provider,
        indexed_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    final_state = graph.invoke(_initial_state())

    assert final_state["status"] == "done"
    assert final_state["current_node"] == "complete_schema_ingestion"
    assert final_state["dialect"] == "postgresql"
    assert final_state["snapshot_id"] == "warehouse-20260515T120000Z"
    assert len(final_state["document_ids"]) == 3
    assert len(final_state["embedding_ids"]) == 3
    assert len(vector_store.records) == 3
    assert snapshot_repository.load("warehouse-20260515T120000Z") is not None


def test_schema_ingestion_graph_retries_failed_introspection_once(tmp_path) -> None:
    snapshot_repository = SchemaSnapshotRepository(tmp_path / "snapshots")
    vector_store = _RecordingVectorStoreRepository()
    provider = _FlakyIntrospectionProvider()
    graph = build_schema_ingestion_graph(
        lambda ref: {"dialect": "postgresql", "host": "localhost"},
        snapshot_repository,
        vector_store,
        lambda content: [float(len(content))],
        provider_factory=lambda dialect: provider,
        indexed_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        max_retries=1,
    )

    final_state = graph.invoke(_initial_state())

    assert final_state["status"] == "done"
    assert final_state["retry_count"] == 1
    assert provider.calls == 2
    assert final_state["snapshot_id"] == "warehouse-20260515T120000Z"


def test_schema_ingestion_graph_marks_failed_when_retries_are_exhausted(tmp_path) -> None:
    snapshot_repository = SchemaSnapshotRepository(tmp_path / "snapshots")
    vector_store = _RecordingVectorStoreRepository()

    class _AlwaysFailingProvider(SchemaIntrospectionProvider):
        def introspect(self, database_id: str, connection_config: dict[str, object]) -> RawIntrospectionResult:
            raise RuntimeError("persistent schema load failure")

    graph = build_schema_ingestion_graph(
        lambda ref: {"dialect": "postgresql", "host": "localhost"},
        snapshot_repository,
        vector_store,
        lambda content: [float(len(content))],
        provider_factory=lambda dialect: _AlwaysFailingProvider(),
        indexed_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        max_retries=0,
    )

    final_state = graph.invoke(_initial_state())

    assert final_state["status"] == "failed"
    assert final_state["current_node"] == "mark_schema_ingestion_failed"
    assert final_state["retry_count"] == 1
    assert final_state["completed_at"] is not None

