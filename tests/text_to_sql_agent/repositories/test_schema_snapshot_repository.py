"""Tests for schema snapshot repository (T-2026-05-15-029)."""

from datetime import datetime, timezone

import pytest

from text_to_sql_agent.models import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeySchema,
    TableSchema,
)
from text_to_sql_agent.repositories import SchemaSnapshotRepository


@pytest.fixture
def repository(tmp_path) -> SchemaSnapshotRepository:
    """Create a snapshot repository in a temporary directory."""
    return SchemaSnapshotRepository(tmp_path)


@pytest.fixture
def sample_schema() -> DatabaseSchema:
    """Create a representative schema snapshot for persistence tests."""
    return DatabaseSchema(
        database_id="warehouse",
        dialect="postgresql",
        snapshot_id="warehouse-20260515T120000Z",
        created_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            TableSchema(
                name="users",
                table_type="TABLE",
                schema_namespace="public",
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
                        name="email",
                        data_type="text",
                        is_nullable=False,
                        is_primary_key=False,
                        is_foreign_key=False,
                        ordinal_position=2,
                    ),
                ],
                primary_keys=["id"],
            ),
            TableSchema(
                name="orders",
                table_type="TABLE",
                schema_namespace="public",
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
                        name="user_id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=False,
                        is_foreign_key=True,
                        ordinal_position=2,
                    ),
                ],
                foreign_keys=[
                    ForeignKeySchema(
                        from_column="user_id",
                        to_table="users",
                        to_column="id",
                    )
                ],
                primary_keys=["id"],
            ),
        ],
    )


def test_save_returns_schema_snapshot_ref(
    repository: SchemaSnapshotRepository,
    sample_schema: DatabaseSchema,
) -> None:
    """Saving a schema should return a populated snapshot reference."""
    snapshot_ref = repository.save(sample_schema)

    assert snapshot_ref.snapshot_id == sample_schema.snapshot_id
    assert snapshot_ref.database_id == sample_schema.database_id
    assert snapshot_ref.dialect == sample_schema.dialect
    assert snapshot_ref.table_count == 2
    assert snapshot_ref.status == "fresh"


def test_save_writes_snapshot_file(
    repository: SchemaSnapshotRepository,
    sample_schema: DatabaseSchema,
) -> None:
    """Saving should create a JSON file on disk."""
    repository.save(sample_schema)

    expected_path = repository.storage_dir / f"{sample_schema.snapshot_id}.json"
    assert expected_path.exists()


def test_load_round_trips_saved_schema(
    repository: SchemaSnapshotRepository,
    sample_schema: DatabaseSchema,
) -> None:
    """Loading a saved snapshot should reproduce the original schema."""
    repository.save(sample_schema)

    loaded = repository.load(sample_schema.snapshot_id)

    assert loaded == sample_schema


def test_list_returns_saved_snapshot_refs(
    repository: SchemaSnapshotRepository,
    sample_schema: DatabaseSchema,
) -> None:
    """Listing should return the stored snapshot reference."""
    repository.save(sample_schema)

    refs = repository.list()

    assert len(refs) == 1
    assert refs[0].snapshot_id == sample_schema.snapshot_id
    assert refs[0].table_count == 2


def test_list_filters_by_database_id(
    repository: SchemaSnapshotRepository,
    sample_schema: DatabaseSchema,
) -> None:
    """Listing should support database-scoped filtering."""
    repository.save(sample_schema)
    repository.save(
        sample_schema.model_copy(
            update={
                "snapshot_id": "other-20260515T120000Z",
                "database_id": "analytics",
            }
        )
    )

    refs = repository.list(database_id="warehouse")

    assert len(refs) == 1
    assert refs[0].database_id == "warehouse"


def test_delete_removes_snapshot_file(
    repository: SchemaSnapshotRepository,
    sample_schema: DatabaseSchema,
) -> None:
    """Deleting a snapshot should remove the on-disk file."""
    repository.save(sample_schema)

    assert repository.delete(sample_schema.snapshot_id) is True
    assert not (repository.storage_dir / f"{sample_schema.snapshot_id}.json").exists()


def test_delete_returns_false_for_missing_snapshot(
    repository: SchemaSnapshotRepository,
) -> None:
    """Deleting a missing snapshot should return False."""
    assert repository.delete("missing-snapshot") is False


def test_load_missing_snapshot_raises(repository: SchemaSnapshotRepository) -> None:
    """Loading a missing snapshot should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        repository.load("missing-snapshot")


def test_repository_creates_storage_directory(tmp_path) -> None:
    """Repository should create the storage directory if needed."""
    storage_dir = tmp_path / "snapshots"

    repository = SchemaSnapshotRepository(storage_dir)

    assert repository.storage_dir.exists()
    assert repository.storage_dir.is_dir()