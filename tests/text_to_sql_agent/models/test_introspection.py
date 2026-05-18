"""Tests for raw introspection Pydantic models (T-2026-05-15-019)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from text_to_sql_agent.models.introspection import (
    RawColumnMeta,
    RawForeignKeyMeta,
    RawIndexMeta,
    RawIntrospectionResult,
    RawTableMeta,
)


# ---------------------------------------------------------------------------
# RawColumnMeta
# ---------------------------------------------------------------------------


def test_raw_column_meta_required_fields() -> None:
    col = RawColumnMeta(
        name="id",
        data_type="INTEGER",
        is_nullable=False,
        is_primary_key=True,
        is_unique=True,
        ordinal_position=1,
    )
    assert col.name == "id"
    assert col.is_primary_key is True
    assert col.default_value is None
    assert col.character_maximum_length is None
    assert col.numeric_precision is None
    assert col.numeric_scale is None


def test_raw_column_meta_optional_fields() -> None:
    col = RawColumnMeta(
        name="username",
        data_type="VARCHAR",
        is_nullable=False,
        is_primary_key=False,
        is_unique=True,
        ordinal_position=2,
        default_value="anonymous",
        character_maximum_length=255,
    )
    assert col.default_value == "anonymous"
    assert col.character_maximum_length == 255


def test_raw_column_meta_missing_required_raises() -> None:
    with pytest.raises(ValidationError):
        RawColumnMeta(name="x", data_type="INT")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# RawForeignKeyMeta
# ---------------------------------------------------------------------------


def test_raw_foreign_key_meta_full() -> None:
    fk = RawForeignKeyMeta(
        constraint_name="fk_orders_customer",
        from_table="orders",
        from_column="customer_id",
        to_table="customers",
        to_column="id",
        on_update="NO ACTION",
        on_delete="CASCADE",
    )
    assert fk.to_table == "customers"
    assert fk.on_delete == "CASCADE"


def test_raw_foreign_key_meta_optional_actions_default_none() -> None:
    fk = RawForeignKeyMeta(
        constraint_name="fk_x",
        from_table="a",
        from_column="b_id",
        to_table="b",
        to_column="id",
    )
    assert fk.on_update is None
    assert fk.on_delete is None


# ---------------------------------------------------------------------------
# RawIndexMeta
# ---------------------------------------------------------------------------


def test_raw_index_meta_basic() -> None:
    idx = RawIndexMeta(
        index_name="idx_orders_status",
        table_name="orders",
        columns=["status", "created_at"],
        is_unique=False,
    )
    assert idx.columns == ["status", "created_at"]
    assert idx.index_type is None


def test_raw_index_meta_with_type() -> None:
    idx = RawIndexMeta(
        index_name="idx_users_email",
        table_name="users",
        columns=["email"],
        is_unique=True,
        index_type="BTREE",
    )
    assert idx.is_unique is True
    assert idx.index_type == "BTREE"


# ---------------------------------------------------------------------------
# RawTableMeta
# ---------------------------------------------------------------------------


def _make_column(name: str = "id", ordinal: int = 1) -> RawColumnMeta:
    return RawColumnMeta(
        name=name,
        data_type="INTEGER",
        is_nullable=False,
        is_primary_key=(name == "id"),
        is_unique=(name == "id"),
        ordinal_position=ordinal,
    )


def test_raw_table_meta_defaults() -> None:
    table = RawTableMeta(name="orders", table_type="TABLE")
    assert table.columns == []
    assert table.foreign_keys == []
    assert table.indexes == []
    assert table.schema_name is None
    assert table.row_count_estimate is None
    assert table.comment is None


def test_raw_table_meta_with_columns() -> None:
    col = _make_column("id", 1)
    table = RawTableMeta(
        name="orders",
        table_type="TABLE",
        columns=[col],
        schema_name="public",
        row_count_estimate=5000,
        comment="Customer purchase records",
    )
    assert len(table.columns) == 1
    assert table.schema_name == "public"
    assert table.row_count_estimate == 5000


def test_raw_table_meta_view_type() -> None:
    table = RawTableMeta(name="v_active_users", table_type="VIEW")
    assert table.table_type == "VIEW"


# ---------------------------------------------------------------------------
# RawIntrospectionResult
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_raw_introspection_result_empty_db() -> None:
    result = RawIntrospectionResult(
        database_id="db-001",
        dialect="sqlite",
        introspected_at=_now(),
    )
    assert result.database_id == "db-001"
    assert result.dialect == "sqlite"
    assert result.tables == []
    assert result.warnings == []


def test_raw_introspection_result_with_tables_and_warnings() -> None:
    col = _make_column("id", 1)
    table = RawTableMeta(name="users", table_type="TABLE", columns=[col])
    result = RawIntrospectionResult(
        database_id="db-002",
        dialect="postgresql",
        introspected_at=_now(),
        tables=[table],
        warnings=["row_count_estimate unavailable for materialized views"],
    )
    assert len(result.tables) == 1
    assert result.tables[0].name == "users"
    assert len(result.warnings) == 1


def test_raw_introspection_result_serialization_roundtrip() -> None:
    col = _make_column("id", 1)
    table = RawTableMeta(name="products", table_type="TABLE", columns=[col])
    result = RawIntrospectionResult(
        database_id="db-003",
        dialect="mysql",
        introspected_at=_now(),
        tables=[table],
    )
    dumped = result.model_dump()
    restored = RawIntrospectionResult.model_validate(dumped)
    assert restored.database_id == result.database_id
    assert restored.tables[0].name == "products"
    assert restored.tables[0].columns[0].name == "id"
