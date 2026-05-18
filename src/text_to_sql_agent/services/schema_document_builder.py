"""Schema document building service."""

from __future__ import annotations

import re

from text_to_sql_agent.models import ColumnSchema, DatabaseSchema, SchemaDocument, TableSchema


def build_schema_documents(schema: DatabaseSchema) -> list[SchemaDocument]:
    """Convert a canonical schema into semantic documents for retrieval."""
    documents: list[SchemaDocument] = []

    for table in sorted(schema.tables, key=lambda table: (table.schema_namespace or "", table.name)):
        documents.extend(_build_table_documents(schema, table))

    return documents


def _build_table_documents(schema: DatabaseSchema, table: TableSchema) -> list[SchemaDocument]:
    documents: list[SchemaDocument] = []
    ordered_columns = sorted(table.columns, key=lambda column: column.ordinal_position)
    ordered_column_names = [column.name for column in ordered_columns]

    documents.append(
        SchemaDocument(
            doc_id=_build_doc_id(schema.snapshot_id, table.name, "table"),
            database_id=schema.database_id,
            snapshot_id=schema.snapshot_id,
            granularity="table",
            table_name=table.name,
            column_names=ordered_column_names,
            content=_build_table_content(table),
            domain_tags=table.domain_tags,
            metadata=_build_metadata(schema, table, "table"),
        )
    )

    if table.columns:
        documents.append(
            SchemaDocument(
                doc_id=_build_doc_id(schema.snapshot_id, table.name, "column_group"),
                database_id=schema.database_id,
                snapshot_id=schema.snapshot_id,
                granularity="column_group",
                table_name=table.name,
                column_names=ordered_column_names,
                content=_build_column_group_content(table),
                domain_tags=table.domain_tags,
                metadata=_build_metadata(schema, table, "column_group"),
            )
        )

    for foreign_key in table.foreign_keys:
        documents.append(
            SchemaDocument(
                doc_id=_build_doc_id(
                    schema.snapshot_id,
                    table.name,
                    "relationship",
                    foreign_key.from_column,
                    foreign_key.to_table,
                    foreign_key.to_column,
                ),
                database_id=schema.database_id,
                snapshot_id=schema.snapshot_id,
                granularity="relationship",
                table_name=table.name,
                column_names=[foreign_key.from_column, foreign_key.to_column],
                content=_build_relationship_content(table, foreign_key),
                domain_tags=table.domain_tags,
                metadata=_build_metadata(schema, table, "relationship", foreign_key.from_column),
            )
        )

    return documents


def _build_table_content(table: TableSchema) -> str:
    column_summaries = [
        _describe_column(column)
        for column in sorted(table.columns, key=lambda column: column.ordinal_position)
    ]
    namespace_prefix = f"Schema {table.schema_namespace}. " if table.schema_namespace else ""
    description_part = f" {table.description}." if table.description else ""
    primary_keys = ", ".join(table.primary_keys) if table.primary_keys else "none"
    column_text = "; ".join(column_summaries) if column_summaries else "No columns discovered."

    return (
        f"{namespace_prefix}Table {table.name} ({table.table_type})."
        f" Primary keys: {primary_keys}.{description_part} Columns: {column_text}"
    ).strip()


def _build_column_group_content(table: TableSchema) -> str:
    columns = [
        _describe_column(column)
        for column in sorted(table.columns, key=lambda column: column.ordinal_position)
    ]
    if not columns:
        return f"Table {table.name} has no columns discovered."

    return f"Table {table.name} column group: " + "; ".join(columns)


def _build_relationship_content(table: TableSchema, foreign_key) -> str:
    return (
        f"Table {table.name} relationship: column {foreign_key.from_column} references "
        f"{foreign_key.to_table}.{foreign_key.to_column}."
    )


def _describe_column(column: ColumnSchema) -> str:
    markers: list[str] = []
    if column.is_primary_key:
        markers.append("PK")
    if column.is_foreign_key:
        markers.append("FK")

    marker_suffix = f" ({', '.join(markers)})" if markers else ""
    alias_suffix = f" aka {column.business_alias}" if column.business_alias else ""
    description_suffix = f" - {column.description}" if column.description else ""

    return f"{column.name}: {column.data_type}{marker_suffix}{alias_suffix}{description_suffix}"


def _build_metadata(
    schema: DatabaseSchema,
    table: TableSchema,
    granularity: str,
    relationship_column: str | None = None,
) -> dict[str, str]:
    metadata = {
        "granularity": granularity,
        "table_type": table.table_type,
        "schema_namespace": table.schema_namespace or "",
        "snapshot_version": str(schema.version),
    }
    if relationship_column is not None:
        metadata["relationship_column"] = relationship_column
    if table.description:
        metadata["table_description"] = table.description
    return {key: value for key, value in metadata.items() if value != ""}


def _build_doc_id(snapshot_id: str, table_name: str, granularity: str, *parts: str) -> str:
    tokens = [snapshot_id, table_name, granularity, *parts]
    slug = "--".join(_slugify_token(token) for token in tokens if token)
    return slug


def _slugify_token(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-") or "item"