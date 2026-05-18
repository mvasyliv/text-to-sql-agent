"""Tests for schema normalization service (T-2026-05-15-028)."""

from datetime import datetime, timezone

from text_to_sql_agent.models import (
    RawColumnMeta,
    RawForeignKeyMeta,
    RawIntrospectionResult,
    RawTableMeta,
)
from text_to_sql_agent.services import build_snapshot_id, normalize_raw_schema


def test_build_snapshot_id_is_deterministic_and_safe() -> None:
    """Snapshot identifiers should be filesystem-friendly and time-based."""
    raw_result = RawIntrospectionResult(
        database_id="Prod Warehouse / EU",
        dialect="postgresql",
        introspected_at=datetime(2026, 5, 15, 12, 30, 45, tzinfo=timezone.utc),
    )

    assert build_snapshot_id(raw_result) == "prod-warehouse-eu-20260515T123045Z"


def test_normalize_raw_schema_uses_explicit_snapshot_id_when_provided() -> None:
    """Explicit snapshot identifiers should override generated values."""
    raw_result = RawIntrospectionResult(
        database_id="analytics",
        dialect="postgresql",
        introspected_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    schema = normalize_raw_schema(raw_result, snapshot_id="snapshot-123")

    assert schema.snapshot_id == "snapshot-123"


def test_normalize_raw_schema_maps_table_type_namespace_and_comment() -> None:
    """Normalization should map table metadata onto the canonical table contract."""
    raw_result = RawIntrospectionResult(
        database_id="warehouse",
        dialect="POSTGRESQL",
        introspected_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            RawTableMeta(
                name="users",
                table_type="BASE TABLE",
                schema_name="public",
                comment="Application users",
            )
        ],
    )

    schema = normalize_raw_schema(raw_result)

    assert schema.dialect == "postgresql"
    assert schema.tables[0].table_type == "TABLE"
    assert schema.tables[0].schema_namespace == "public"
    assert schema.tables[0].description == "Application users"


def test_normalize_raw_schema_marks_primary_and_foreign_keys() -> None:
    """Columns should be annotated with PK and FK flags and preserve PK order."""
    raw_result = RawIntrospectionResult(
        database_id="warehouse",
        dialect="postgresql",
        introspected_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            RawTableMeta(
                name="orders",
                table_type="TABLE",
                columns=[
                    RawColumnMeta(
                        name="user_id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=False,
                        is_unique=False,
                        ordinal_position=2,
                    ),
                    RawColumnMeta(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                        is_unique=True,
                        ordinal_position=1,
                    ),
                ],
                foreign_keys=[
                    RawForeignKeyMeta(
                        constraint_name="fk_orders_user",
                        from_table="orders",
                        from_column="user_id",
                        to_table="users",
                        to_column="id",
                    )
                ],
            )
        ],
    )

    schema = normalize_raw_schema(raw_result)
    table = schema.tables[0]

    assert table.primary_keys == ["id"]
    assert [column.name for column in table.columns] == ["id", "user_id"]
    assert table.columns[0].is_primary_key is True
    assert table.columns[1].is_foreign_key is True
    assert table.foreign_keys[0].from_column == "user_id"


def test_normalize_raw_schema_deduplicates_foreign_keys() -> None:
    """Duplicate FK metadata should collapse to one canonical relationship."""
    duplicate_foreign_key = RawForeignKeyMeta(
        constraint_name="fk_orders_user",
        from_table="orders",
        from_column="user_id",
        to_table="users",
        to_column="id",
    )
    raw_result = RawIntrospectionResult(
        database_id="warehouse",
        dialect="postgresql",
        introspected_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            RawTableMeta(
                name="orders",
                table_type="TABLE",
                columns=[
                    RawColumnMeta(
                        name="user_id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=False,
                        is_unique=False,
                        ordinal_position=1,
                    )
                ],
                foreign_keys=[duplicate_foreign_key, duplicate_foreign_key],
            )
        ],
    )

    schema = normalize_raw_schema(raw_result)

    assert len(schema.tables[0].foreign_keys) == 1
    assert schema.tables[0].columns[0].is_foreign_key is True


def test_normalize_raw_schema_normalizes_postgresql_types() -> None:
    """Common PostgreSQL aliases should map to stable canonical types."""
    raw_result = RawIntrospectionResult(
        database_id="warehouse",
        dialect="postgresql",
        introspected_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            RawTableMeta(
                name="metrics",
                table_type="TABLE",
                columns=[
                    RawColumnMeta(
                        name="label",
                        data_type="character varying",
                        is_nullable=False,
                        is_primary_key=False,
                        is_unique=False,
                        ordinal_position=1,
                    ),
                    RawColumnMeta(
                        name="captured_at",
                        data_type="timestamp without time zone",
                        is_nullable=False,
                        is_primary_key=False,
                        is_unique=False,
                        ordinal_position=2,
                    ),
                    RawColumnMeta(
                        name="payload",
                        data_type="jsonb",
                        is_nullable=True,
                        is_primary_key=False,
                        is_unique=False,
                        ordinal_position=3,
                    ),
                ],
            )
        ],
    )

    schema = normalize_raw_schema(raw_result)
    columns = schema.tables[0].columns

    assert columns[0].data_type == "text"
    assert columns[1].data_type == "timestamp"
    assert columns[2].data_type == "json"


def test_normalize_raw_schema_normalizes_sqlite_affinity_types() -> None:
    """SQLite types should normalize according to affinity rules."""
    raw_result = RawIntrospectionResult(
        database_id="local-db",
        dialect="sqlite",
        introspected_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            RawTableMeta(
                name="events",
                table_type="table",
                columns=[
                    RawColumnMeta(
                        name="id",
                        data_type="INTEGER",
                        is_nullable=False,
                        is_primary_key=True,
                        is_unique=True,
                        ordinal_position=1,
                    ),
                    RawColumnMeta(
                        name="title",
                        data_type="VARCHAR(255)",
                        is_nullable=False,
                        is_primary_key=False,
                        is_unique=False,
                        ordinal_position=2,
                    ),
                    RawColumnMeta(
                        name="amount",
                        data_type="DECIMAL(10,2)",
                        is_nullable=True,
                        is_primary_key=False,
                        is_unique=False,
                        ordinal_position=3,
                    ),
                ],
            )
        ],
    )

    schema = normalize_raw_schema(raw_result)
    columns = schema.tables[0].columns

    assert schema.tables[0].table_type == "TABLE"
    assert columns[0].data_type == "integer"
    assert columns[1].data_type == "text"
    assert columns[2].data_type == "numeric"


def test_normalize_raw_schema_preserves_created_at_and_version() -> None:
    """Canonical schema should keep the introspection timestamp and default version."""
    timestamp = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    raw_result = RawIntrospectionResult(
        database_id="warehouse",
        dialect="postgresql",
        introspected_at=timestamp,
    )

    schema = normalize_raw_schema(raw_result)

    assert schema.created_at == timestamp
    assert schema.version == 1