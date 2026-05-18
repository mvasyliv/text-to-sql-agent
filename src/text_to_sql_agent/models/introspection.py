"""Raw introspection models — vendor-specific metadata shapes before normalization."""

from datetime import datetime

from pydantic import BaseModel, Field


class RawColumnMeta(BaseModel):
    """Raw metadata for a single column as returned by a dialect-specific introspector."""

    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    is_unique: bool
    ordinal_position: int
    default_value: str | None = None
    character_maximum_length: int | None = None
    numeric_precision: int | None = None
    numeric_scale: int | None = None


class RawForeignKeyMeta(BaseModel):
    """Raw metadata for a single foreign key constraint."""

    constraint_name: str
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    on_update: str | None = None
    on_delete: str | None = None


class RawIndexMeta(BaseModel):
    """Raw metadata for a single index."""

    index_name: str
    table_name: str
    columns: list[str]
    is_unique: bool
    index_type: str | None = None


class RawTableMeta(BaseModel):
    """Raw metadata for a single table or view."""

    name: str
    table_type: str = Field(
        description="One of: TABLE, VIEW, MATERIALIZED_VIEW",
    )
    columns: list[RawColumnMeta] = Field(default_factory=list)
    foreign_keys: list[RawForeignKeyMeta] = Field(default_factory=list)
    indexes: list[RawIndexMeta] = Field(default_factory=list)
    schema_name: str | None = None
    row_count_estimate: int | None = None
    comment: str | None = None


class RawIntrospectionResult(BaseModel):
    """Full raw introspection output for a single database connection."""

    database_id: str
    dialect: str
    introspected_at: datetime
    tables: list[RawTableMeta] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
