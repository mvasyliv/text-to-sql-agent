"""Tests for canonical schema Pydantic models (T-2026-05-15-020)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from text_to_sql_agent.models.schema import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeySchema,
    TableSchema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_column(
    name: str = "id",
    data_type: str = "INTEGER",
    ordinal: int = 1,
    is_pk: bool = True,
    is_fk: bool = False,
) -> ColumnSchema:
    return ColumnSchema(
        name=name,
        data_type=data_type,
        is_nullable=False,
        is_primary_key=is_pk,
        is_foreign_key=is_fk,
        ordinal_position=ordinal,
    )


# ---------------------------------------------------------------------------
# ForeignKeySchema
# ---------------------------------------------------------------------------


def test_foreign_key_schema_basic() -> None:
    fk = ForeignKeySchema(from_column="customer_id", to_table="customers", to_column="id")
    assert fk.from_column == "customer_id"
    assert fk.to_table == "customers"
    assert fk.to_column == "id"


def test_foreign_key_schema_missing_field_raises() -> None:
    with pytest.raises(ValidationError):
        ForeignKeySchema(from_column="x", to_table="y")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ColumnSchema
# ---------------------------------------------------------------------------


def test_column_schema_required_fields() -> None:
    col = _make_column()
    assert col.name == "id"
    assert col.is_primary_key is True
    assert col.is_foreign_key is False
    assert col.default_value is None
    assert col.description is None
    assert col.business_alias is None


def test_column_schema_optional_fields() -> None:
    col = ColumnSchema(
        name="status",
        data_type="VARCHAR",
        is_nullable=False,
        is_primary_key=False,
        is_foreign_key=False,
        ordinal_position=3,
        default_value="active",
        description="Current order status",
        business_alias="order_status",
    )
    assert col.default_value == "active"
    assert col.description == "Current order status"
    assert col.business_alias == "order_status"


def test_column_schema_missing_required_raises() -> None:
    with pytest.raises(ValidationError):
        ColumnSchema(name="x", data_type="INT")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TableSchema
# ---------------------------------------------------------------------------


def test_table_schema_defaults() -> None:
    table = TableSchema(name="orders", table_type="TABLE")
    assert table.columns == []
    assert table.foreign_keys == []
    assert table.primary_keys == []
    assert table.schema_namespace is None
    assert table.description is None
    assert table.domain_tags == []


def test_table_schema_with_columns_and_fks() -> None:
    col_id = _make_column("id", ordinal=1)
    col_cid = _make_column("customer_id", data_type="INTEGER", ordinal=2, is_pk=False, is_fk=True)
    fk = ForeignKeySchema(from_column="customer_id", to_table="customers", to_column="id")
    table = TableSchema(
        name="orders",
        table_type="TABLE",
        columns=[col_id, col_cid],
        foreign_keys=[fk],
        primary_keys=["id"],
        schema_namespace="public",
        description="Customer purchase records",
        domain_tags=["sales", "finance"],
    )
    assert len(table.columns) == 2
    assert len(table.foreign_keys) == 1
    assert table.primary_keys == ["id"]
    assert table.domain_tags == ["sales", "finance"]


def test_table_schema_view_type() -> None:
    table = TableSchema(name="v_active_users", table_type="VIEW")
    assert table.table_type == "VIEW"


# ---------------------------------------------------------------------------
# DatabaseSchema
# ---------------------------------------------------------------------------


def test_database_schema_defaults() -> None:
    schema = DatabaseSchema(
        database_id="db-001",
        dialect="sqlite",
        snapshot_id="snap-abc",
        created_at=_now(),
    )
    assert schema.tables == []
    assert schema.version == 1


def test_database_schema_with_tables() -> None:
    col = _make_column()
    table = TableSchema(name="users", table_type="TABLE", columns=[col], primary_keys=["id"])
    schema = DatabaseSchema(
        database_id="db-002",
        dialect="postgresql",
        snapshot_id="snap-xyz",
        created_at=_now(),
        tables=[table],
        version=2,
    )
    assert len(schema.tables) == 1
    assert schema.tables[0].name == "users"
    assert schema.version == 2


def test_database_schema_missing_required_raises() -> None:
    with pytest.raises(ValidationError):
        DatabaseSchema(database_id="db-003", dialect="sqlite")  # type: ignore[call-arg]


def test_database_schema_serialization_roundtrip() -> None:
    col = _make_column("id", ordinal=1)
    col_fk = _make_column("org_id", data_type="INTEGER", ordinal=2, is_pk=False, is_fk=True)
    fk = ForeignKeySchema(from_column="org_id", to_table="organizations", to_column="id")
    table = TableSchema(
        name="employees",
        table_type="TABLE",
        columns=[col, col_fk],
        foreign_keys=[fk],
        primary_keys=["id"],
        domain_tags=["hr"],
    )
    schema = DatabaseSchema(
        database_id="db-004",
        dialect="mysql",
        snapshot_id="snap-001",
        created_at=_now(),
        tables=[table],
    )
    dumped = schema.model_dump()
    restored = DatabaseSchema.model_validate(dumped)
    assert restored.database_id == "db-004"
    assert restored.tables[0].name == "employees"
    assert restored.tables[0].foreign_keys[0].to_table == "organizations"
    assert restored.tables[0].columns[1].is_foreign_key is True
