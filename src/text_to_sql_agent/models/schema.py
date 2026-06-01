"""Canonical schema models — normalized internal contract shared across all layers."""

from datetime import datetime

from pydantic import BaseModel, Field


class ForeignKeySchema(BaseModel):
    """Canonical representation of a foreign key relationship."""

    from_column: str = Field(description="Name of the column that contains the foreign key")
    to_table: str = Field(description="Name of the referenced table")
    to_column: str = Field(description="Name of the referenced column")


class ColumnSchema(BaseModel):
    """Canonical representation of a single table column."""

    name: str = Field(description="Name of the column")
    data_type: str = Field(description="SQL data type of the column")
    is_nullable: bool = Field(description="Whether the column allows NULL values")
    is_primary_key: bool = Field(description="Whether the column is part of the primary key")
    is_foreign_key: bool = Field(description="Whether the column is a foreign key")
    ordinal_position: int = Field(description="Position of the column in the table (1-based)")
    default_value: str | None = Field(default=None, description="Default value for the column")
    description: str | None = Field(default=None, description="Business description of the column")
    business_alias: str | None = Field(default=None, description="Business-friendly name for the column")


class TableSchema(BaseModel):
    """Canonical representation of a table or view."""

    name: str = Field(description="Name of the table or view")
    table_type: str = Field(
        description="One of: TABLE, VIEW, MATERIALIZED_VIEW",
    )
    columns: list[ColumnSchema] = Field(default_factory=list, description="List of columns in the table")
    foreign_keys: list[ForeignKeySchema] = Field(default_factory=list, description="List of foreign key relationships")
    primary_keys: list[str] = Field(default_factory=list, description="List of primary key column names")
    schema_namespace: str | None = Field(default=None, description="Schema or namespace name (e.g., 'public', 'dbo')")
    description: str | None = Field(default=None, description="Business description of the table")
    domain_tags: list[str] = Field(default_factory=list, description="Domain or business classification tags")


class DatabaseSchema(BaseModel):
    """Canonical normalized schema for a single database connection."""

    database_id: str = Field(description="Unique identifier for the database")
    dialect: str = Field(description="SQL dialect used by the database (e.g., 'postgresql', 'mysql', 'sqlite')")
    snapshot_id: str = Field(description="Unique identifier for this schema snapshot")
    created_at: datetime = Field(description="Timestamp when the schema snapshot was created")
    tables: list[TableSchema] = Field(default_factory=list, description="List of tables and views in the database")
    version: int = Field(default=1, description="Schema version number for tracking changes")
