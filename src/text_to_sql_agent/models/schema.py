"""Canonical schema models — normalized internal contract shared across all layers."""

from datetime import datetime

from pydantic import BaseModel, Field


class ForeignKeySchema(BaseModel):
    """Canonical representation of a foreign key relationship."""

    from_column: str
    to_table: str
    to_column: str


class ColumnSchema(BaseModel):
    """Canonical representation of a single table column."""

    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    is_foreign_key: bool
    ordinal_position: int
    default_value: str | None = None
    description: str | None = None
    business_alias: str | None = None


class TableSchema(BaseModel):
    """Canonical representation of a table or view."""

    name: str
    table_type: str = Field(
        description="One of: TABLE, VIEW, MATERIALIZED_VIEW",
    )
    columns: list[ColumnSchema] = Field(default_factory=list)
    foreign_keys: list[ForeignKeySchema] = Field(default_factory=list)
    primary_keys: list[str] = Field(default_factory=list)
    schema_namespace: str | None = None
    description: str | None = None
    domain_tags: list[str] = Field(default_factory=list)


class DatabaseSchema(BaseModel):
    """Canonical normalized schema for a single database connection."""

    database_id: str
    dialect: str
    snapshot_id: str
    created_at: datetime
    tables: list[TableSchema] = Field(default_factory=list)
    version: int = 1
