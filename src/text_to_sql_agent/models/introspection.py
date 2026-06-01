"""Raw introspection models — vendor-specific metadata shapes before normalization."""

from datetime import datetime

from pydantic import BaseModel, Field


class RawColumnMeta(BaseModel):
    """Raw metadata for a single column as returned by a dialect-specific introspector."""

    name: str = Field(description="Column name")
    data_type: str = Field(description="SQL data type of the column")
    is_nullable: bool = Field(description="Whether the column allows NULL values")
    is_primary_key: bool = Field(description="Whether the column is part of the primary key")
    is_unique: bool = Field(description="Whether the column has a unique constraint")
    ordinal_position: int = Field(description="Position of the column in the table (1-based)")
    default_value: str | None = Field(default=None, description="Default value for the column")
    character_maximum_length: int | None = Field(default=None, description="Maximum length for character columns")
    numeric_precision: int | None = Field(default=None, description="Precision for numeric columns")
    numeric_scale: int | None = Field(default=None, description="Scale for numeric columns")


class RawForeignKeyMeta(BaseModel):
    """Raw metadata for a single foreign key constraint."""

    constraint_name: str = Field(description="Name of the foreign key constraint")
    from_table: str = Field(description="Name of the table that owns the foreign key column")
    from_column: str = Field(description="Name of the foreign key column in the source table")
    to_table: str = Field(description="Name of the referenced table")
    to_column: str = Field(description="Name of the referenced column")
    on_update: str | None = Field(default=None, description="Referential action applied on source-row update")
    on_delete: str | None = Field(default=None, description="Referential action applied on source-row delete")


class RawIndexMeta(BaseModel):
    """Raw metadata for a single index."""

    index_name: str = Field(description="Name of the index")
    table_name: str = Field(description="Name of the table that owns the index")
    columns: list[str] = Field(description="Ordered list of indexed column names")
    is_unique: bool = Field(description="Whether the index enforces uniqueness")
    index_type: str | None = Field(default=None, description="Database-specific index type")


class RawTableMeta(BaseModel):
    """Raw metadata for a single table or view."""

    name: str = Field(description="Name of the table or view")
    table_type: str = Field(
        description="One of: TABLE, VIEW, MATERIALIZED_VIEW",
    )
    columns: list[RawColumnMeta] = Field(default_factory=list, description="List of table columns")
    foreign_keys: list[RawForeignKeyMeta] = Field(default_factory=list, description="List of foreign key constraints")
    indexes: list[RawIndexMeta] = Field(default_factory=list, description="List of indexes defined on the table")
    schema_name: str | None = Field(default=None, description="Schema or namespace that owns the table")
    row_count_estimate: int | None = Field(default=None, description="Estimated number of rows in the table")
    comment: str | None = Field(default=None, description="Table-level comment provided by the database")


class RawIntrospectionResult(BaseModel):
    """Full raw introspection output for a single database connection."""

    database_id: str = Field(description="Unique identifier of the introspected database")
    dialect: str = Field(description="SQL dialect used by the introspected database")
    introspected_at: datetime = Field(description="Timestamp when introspection was executed")
    tables: list[RawTableMeta] = Field(default_factory=list, description="List of introspected tables and views")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings produced during introspection")
