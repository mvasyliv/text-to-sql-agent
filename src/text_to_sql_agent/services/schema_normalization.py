"""Schema normalization service."""

from __future__ import annotations

import re
from datetime import timezone

from text_to_sql_agent.models import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeySchema,
    RawForeignKeyMeta,
    RawIntrospectionResult,
    RawTableMeta,
    TableSchema,
)


def normalize_raw_schema(
    raw_result: RawIntrospectionResult,
    snapshot_id: str | None = None,
) -> DatabaseSchema:
    """Convert raw introspection output into the canonical database schema."""
    normalized_dialect = raw_result.dialect.strip().lower()
    resolved_snapshot_id = snapshot_id or build_snapshot_id(raw_result)

    tables = [
        _normalize_table(raw_table, normalized_dialect)
        for raw_table in raw_result.tables
    ]

    return DatabaseSchema(
        database_id=raw_result.database_id,
        dialect=normalized_dialect,
        snapshot_id=resolved_snapshot_id,
        created_at=raw_result.introspected_at,
        tables=tables,
    )


def build_snapshot_id(raw_result: RawIntrospectionResult) -> str:
    """Build a deterministic snapshot identifier from database identity and time."""
    slug = _slugify_identifier(raw_result.database_id)
    timestamp = raw_result.introspected_at.astimezone(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    return f"{slug}-{timestamp}"


def _normalize_table(raw_table: RawTableMeta, dialect: str) -> TableSchema:
    deduplicated_foreign_keys = _deduplicate_foreign_keys(raw_table.foreign_keys)
    foreign_key_columns = {foreign_key.from_column for foreign_key in deduplicated_foreign_keys}
    ordered_columns = sorted(raw_table.columns, key=lambda column: column.ordinal_position)

    columns = [
        ColumnSchema(
            name=raw_column.name,
            data_type=_normalize_data_type(raw_column.data_type, dialect),
            is_nullable=raw_column.is_nullable,
            is_primary_key=raw_column.is_primary_key,
            is_foreign_key=raw_column.name in foreign_key_columns,
            ordinal_position=raw_column.ordinal_position,
            default_value=raw_column.default_value,
        )
        for raw_column in ordered_columns
    ]

    primary_keys = [
        raw_column.name
        for raw_column in ordered_columns
        if raw_column.is_primary_key
    ]

    foreign_keys = [
        ForeignKeySchema(
            from_column=foreign_key.from_column,
            to_table=foreign_key.to_table,
            to_column=foreign_key.to_column,
        )
        for foreign_key in deduplicated_foreign_keys
    ]

    return TableSchema(
        name=raw_table.name,
        table_type=_normalize_table_type(raw_table.table_type),
        columns=columns,
        foreign_keys=foreign_keys,
        primary_keys=primary_keys,
        schema_namespace=raw_table.schema_name,
        description=raw_table.comment,
    )


def _normalize_table_type(table_type: str) -> str:
    normalized = table_type.strip().upper().replace(" ", "_")
    if normalized == "BASE_TABLE":
        return "TABLE"
    return normalized


def _normalize_data_type(data_type: str, dialect: str) -> str:
    normalized = data_type.strip().lower()
    base_type = normalized.split("(", 1)[0].strip()

    alias_map = {
        "bool": "boolean",
        "boolean": "boolean",
        "character varying": "text",
        "character": "text",
        "char": "text",
        "varchar": "text",
        "citext": "text",
        "text": "text",
        "datetime": "timestamp",
        "timestamp with time zone": "timestamp",
        "timestamp without time zone": "timestamp",
        "timestamp": "timestamp",
        "decimal": "numeric",
        "numeric": "numeric",
        "double precision": "double",
        "float8": "double",
        "float4": "real",
        "jsonb": "json",
    }

    if base_type in alias_map:
        return alias_map[base_type]

    if dialect == "sqlite":
        if "int" in normalized:
            return "integer"
        if any(token in normalized for token in ("char", "clob", "text")):
            return "text"
        if "blob" in normalized:
            return "blob"
        if any(token in normalized for token in ("real", "floa", "doub")):
            return "real"
        return "numeric"

    return base_type


def _deduplicate_foreign_keys(
    foreign_keys: list[RawForeignKeyMeta],
) -> list[RawForeignKeyMeta]:
    seen: set[tuple[str, str, str]] = set()
    deduplicated: list[RawForeignKeyMeta] = []

    for foreign_key in foreign_keys:
        key = (
            foreign_key.from_column,
            foreign_key.to_table,
            foreign_key.to_column,
        )
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(foreign_key)

    return deduplicated


def _slugify_identifier(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "schema"