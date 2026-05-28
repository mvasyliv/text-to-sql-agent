"""Tests for the schema context agent (T-2026-05-18-042)."""

from unittest.mock import MagicMock, patch

import pytest

from text_to_sql_agent.agents.schema_context_agent import (
    build_schema_context,
    build_schema_context_node,
    format_schema_context,
)
from datetime import datetime, timezone

from text_to_sql_agent.models.schema import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeySchema,
    TableSchema,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _make_schema(
    tables: list[TableSchema] | None = None,
    database_id: str = "testdb",
    dialect: str = "sqlite",
) -> DatabaseSchema:
    return DatabaseSchema(
        database_id=database_id,
        snapshot_id="snap-001",
        dialect=dialect,
        created_at=_NOW,
        tables=tables or [],
    )


def _make_table(name: str, columns: list[str] | None = None) -> TableSchema:
    cols = [
        ColumnSchema(
            name=col,
            data_type="text",
            ordinal_position=i,
            is_nullable=True,
            is_primary_key=(i == 0),
            is_foreign_key=False,
        )
        for i, col in enumerate(columns or ["id", "name"])
    ]
    return TableSchema(name=name, table_type="TABLE", columns=cols)


# ---------------------------------------------------------------------------
# format_schema_context
# ---------------------------------------------------------------------------


class TestFormatSchemaContext:
    def test_includes_database_header(self):
        schema = _make_schema([_make_table("users")])
        result = format_schema_context(schema)
        assert "testdb" in result
        assert "sqlite" in result

    def test_includes_table_name(self):
        schema = _make_schema([_make_table("orders")])
        result = format_schema_context(schema)
        assert "orders" in result

    def test_includes_column_names(self):
        schema = _make_schema([_make_table("users", ["id", "email", "created_at"])])
        result = format_schema_context(schema)
        assert "id" in result
        assert "email" in result
        assert "created_at" in result

    def test_pk_tag_present(self):
        schema = _make_schema([_make_table("users")])
        result = format_schema_context(schema)
        assert "PK" in result

    def test_empty_schema_returns_comment(self):
        schema = _make_schema([])
        result = format_schema_context(schema)
        assert "No tables found" in result

    def test_table_filter_includes_only_requested(self):
        schema = _make_schema([_make_table("users"), _make_table("orders")])
        result = format_schema_context(schema, table_filter=["users"])
        assert "users" in result
        assert "orders" not in result

    def test_table_filter_strips_punctuation(self):
        schema = _make_schema([_make_table("optins")])
        result = format_schema_context(schema, table_filter=["optins?"])
        assert "optins" in result

    def test_table_filter_ignores_stopwords(self):
        schema = _make_schema([_make_table("optins")])
        result = format_schema_context(schema, table_filter=["table", "optins"])
        assert "optins" in result

    def test_foreign_key_shown(self):
        fk = ForeignKeySchema(
            from_column="user_id",
            to_table="users",
            to_column="id",
        )
        table = TableSchema(
            name="orders",
            table_type="TABLE",
            columns=[
                ColumnSchema(
                    name="id",
                    data_type="integer",
                    ordinal_position=0,
                    is_nullable=False,
                    is_primary_key=True,
                    is_foreign_key=False,
                )
            ],
            foreign_keys=[fk],
        )
        schema = _make_schema([table])
        result = format_schema_context(schema)
        assert "user_id" in result
        assert "users" in result

    def test_multiple_tables_all_present(self):
        schema = _make_schema([_make_table("users"), _make_table("orders")])
        result = format_schema_context(schema)
        assert "users" in result
        assert "orders" in result


# ---------------------------------------------------------------------------
# build_schema_context (integration via mock)
# ---------------------------------------------------------------------------


class TestBuildSchemaContext:
    def test_calls_provider_and_returns_string(self):
        fake_raw = MagicMock()
        fake_raw.dialect = "sqlite"
        fake_raw.tables = []
        fake_raw.database_id = "mydb"

        fake_schema = _make_schema([_make_table("users")], database_id="mydb")

        with (
            patch(
                "text_to_sql_agent.agents.schema_context_agent.get_introspection_provider"
            ) as mock_factory,
            patch(
                "text_to_sql_agent.agents.schema_context_agent.normalize_raw_schema",
                return_value=fake_schema,
            ),
        ):
            mock_provider = MagicMock()
            mock_provider.introspect.return_value = fake_raw
            mock_factory.return_value = mock_provider

            result = build_schema_context("mydb", {"path": ":memory:"}, dialect="sqlite")

        assert "mydb" in result
        assert "users" in result
        mock_factory.assert_called_once_with("sqlite")
        mock_provider.introspect.assert_called_once_with("mydb", {"path": ":memory:"})


# ---------------------------------------------------------------------------
# build_schema_context_node (LangGraph adapter)
# ---------------------------------------------------------------------------


class TestBuildSchemaContextNode:
    def _state(self, database_id: str = "mydb", dialect: str = "sqlite") -> dict:
        return {
            "database_id": database_id,
            "dialect": dialect,
            "selected_tables": None,
            "user_id": "u-001",
            "conversation_id": "c-001",
            "message_id": "m-001",
            "user_question": "how many rows?",
            "schema_context": None,
            "generated_sql": None,
            "sql_generation_prompt": None,
            "sql_rationale": None,
            "syntax_valid": None,
            "syntax_errors": [],
            "security_approved": None,
            "security_violations": [],
            "human_approved": None,
            "edited_sql": None,
            "execution_result": None,
            "execution_error": None,
            "chart_spec": None,
            "export_path": None,
            "insight_text": None,
            "status": "pending",
            "error_message": None,
            "log_messages": [],
        }

    def test_success_populates_schema_context(self):
        fake_schema = _make_schema([_make_table("users")])
        with (
            patch(
                "text_to_sql_agent.agents.schema_context_agent.get_introspection_provider"
            ) as mock_factory,
            patch(
                "text_to_sql_agent.agents.schema_context_agent.normalize_raw_schema",
                return_value=fake_schema,
            ),
        ):
            mock_provider = MagicMock()
            mock_provider.introspect.return_value = MagicMock(dialect="sqlite", tables=[])
            mock_factory.return_value = mock_provider

            node = build_schema_context_node({"path": ":memory:"})
            result = node(self._state())

        assert result["schema_context"] is not None
        assert "users" in result["schema_context"]
        assert result["status"] == "validating"
        assert len(result["log_messages"]) == 1

    def test_failure_sets_failed_status(self):
        with patch(
            "text_to_sql_agent.agents.schema_context_agent.get_introspection_provider",
            side_effect=RuntimeError("connection refused"),
        ):
            node = build_schema_context_node({"path": ":memory:"})
            result = node(self._state())

        assert result["status"] == "failed"
        assert result["schema_context"] is None
        assert "connection refused" in result["error_message"]
