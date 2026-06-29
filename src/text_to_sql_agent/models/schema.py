"""Canonical schema models — normalized internal contract shared across all layers."""

from datetime import datetime

from pydantic import BaseModel, Field


class ForeignKeySchema(BaseModel):
    """Canonical representation of a foreign key relationship."""

    from_column: str = Field(description="The column in the source table that references another table.")
    to_table: str = Field(description="The name of the table being referenced.")
    to_column: str = Field(description="The column in the referenced table.")


class ColumnSchema(BaseModel):
    """Canonical representation of a single table column."""

    name: str = Field(description="The name of the column.")
    data_type: str = Field(description="The data type of the column.")
    is_nullable: bool = Field(description="Whether the column allows NULL values.")
    is_primary_key: bool = Field(description="Whether the column is part of the primary key.")
    is_foreign_key: bool = Field(description="Whether the column is a foreign key.")
    ordinal_position: int = Field(description="The ordinal position of the column in the table (starting from 1).")
    default_value: str | None = Field(default=None, description="The default value of the column, if any.")
    description: str | None = Field(default=None, description="A human-readable description of the column.")
    business_alias: str | None = Field(default=None, description="A business alias or friendly name for the column, if any.")


class TableSchema(BaseModel):
    """Canonical representation of a table or view."""

    name: str = Field(description="The name of the table or view.")
    table_type: str = Field(
        description="One of: TABLE, VIEW, MATERIALIZED_VIEW",
    )
    columns: list[ColumnSchema] = Field(
        default_factory=list,
        description="A list of columns defined in the table or view."
    )
    foreign_keys: list[ForeignKeySchema] = Field(
        default_factory=list,
        description="A list of foreign keys defined on the table."
    )
    primary_keys: list[str] = Field(
        default_factory=list,
        description="A list of column names that make up the primary key for the table."
    )
    schema_namespace: str | None = Field(
        default=None,
        description="The schema or namespace this table belongs to, if any."
    )
    description: str | None = Field(
        default=None,
        description="A human-readable description of the table or view."
    )
    domain_tags: list[str] = Field(
        default_factory=list,
        description="A list of business or domain-specific tags assigned to the table."
    )

class DatabaseSchema(BaseModel):
    """Canonical normalized schema for a single database connection."""

    database_id: str = Field(description="The unique identifier for the database.")
    dialect: str = Field(description="The SQL dialect used by the database.")
    snapshot_id: str = Field(description="The unique identifier for the database snapshot.")
    created_at: datetime = Field(description="The timestamp when the schema was created.")
    tables: list[TableSchema] = Field(default_factory=list, description="A list of tables defined in the database.")
    version: int = Field(default=1, description="The version of the schema.")
