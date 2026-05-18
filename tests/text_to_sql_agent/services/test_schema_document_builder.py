"""Tests for schema document building service (T-2026-05-15-030)."""

from datetime import datetime, timezone

from text_to_sql_agent.models import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeySchema,
    TableSchema,
)
from text_to_sql_agent.services import build_schema_documents


def _sample_schema() -> DatabaseSchema:
    return DatabaseSchema(
        database_id="warehouse",
        dialect="postgresql",
        snapshot_id="warehouse-20260515T120000Z",
        created_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
        tables=[
            TableSchema(
                name="orders",
                table_type="TABLE",
                schema_namespace="public",
                description="Customer orders",
                domain_tags=["sales", "orders"],
                columns=[
                    ColumnSchema(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                        is_foreign_key=False,
                        ordinal_position=1,
                        description="Order identifier",
                    ),
                    ColumnSchema(
                        name="customer_id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=False,
                        is_foreign_key=True,
                        ordinal_position=2,
                        business_alias="customer",
                    ),
                ],
                foreign_keys=[
                    ForeignKeySchema(
                        from_column="customer_id",
                        to_table="customers",
                        to_column="id",
                    )
                ],
                primary_keys=["id"],
            )
        ],
    )


def test_build_schema_documents_returns_expected_document_types() -> None:
    """The builder should create table, column_group, and relationship documents."""
    documents = build_schema_documents(_sample_schema())

    assert [document.granularity for document in documents] == [
        "table",
        "column_group",
        "relationship",
    ]


def test_build_schema_documents_uses_deterministic_doc_ids() -> None:
    """Document IDs should be stable and readable."""
    documents = build_schema_documents(_sample_schema())

    assert documents[0].doc_id == "warehouse-20260515t120000z--orders--table"
    assert documents[1].doc_id == "warehouse-20260515t120000z--orders--column-group"
    assert documents[2].doc_id == (
        "warehouse-20260515t120000z--orders--relationship--customer-id--customers--id"
    )


def test_build_schema_documents_includes_human_readable_content() -> None:
    """Content should summarize table, columns, and relationships clearly."""
    documents = build_schema_documents(_sample_schema())

    table_content = documents[0].content
    column_group_content = documents[1].content
    relationship_content = documents[2].content

    assert "Table orders (TABLE)." in table_content
    assert "Primary keys: id." in table_content
    assert "Columns:" in table_content
    assert "customer_id: integer (FK) aka customer" in column_group_content
    assert "Order identifier" in table_content
    assert "orders relationship" in relationship_content
    assert "customer_id references customers.id" in relationship_content


def test_build_schema_documents_preserves_domain_tags_and_metadata() -> None:
    """Domain tags and metadata should be carried into documents."""
    documents = build_schema_documents(_sample_schema())

    for document in documents:
        assert document.database_id == "warehouse"
        assert document.snapshot_id == "warehouse-20260515T120000Z"
        assert document.domain_tags == ["sales", "orders"]
        assert document.metadata["granularity"] == document.granularity
        assert document.metadata["table_type"] == "TABLE"
        assert document.metadata["schema_namespace"] == "public"


def test_build_schema_documents_orders_columns_by_ordinal_position() -> None:
    """Columns in document content should respect ordinal position ordering."""
    schema = _sample_schema().model_copy(
        update={
            "tables": [
                _sample_schema().tables[0].model_copy(
                    update={
                        "columns": [
                            _sample_schema().tables[0].columns[1],
                            _sample_schema().tables[0].columns[0],
                        ]
                    }
                )
            ]
        }
    )

    documents = build_schema_documents(schema)

    assert documents[0].column_names == ["id", "customer_id"]
    assert documents[1].column_names == ["id", "customer_id"]