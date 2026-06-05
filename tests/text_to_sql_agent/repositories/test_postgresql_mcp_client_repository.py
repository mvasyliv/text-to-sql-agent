"""Tests for the PostgreSQL MCP client repository."""

from unittest.mock import MagicMock

import psycopg2

from text_to_sql_agent.models import MCPExecuteRequest, MCPHealthRequest, MCPSchemaRequest, MCPToolRequestMeta
from text_to_sql_agent.repositories import PostgreSQLMCPClientRepository


def _meta() -> MCPToolRequestMeta:
    return MCPToolRequestMeta(request_id="req-001", user_id="u-001", conversation_id="c-001")


def _build_repository() -> PostgreSQLMCPClientRepository:
    return PostgreSQLMCPClientRepository(
        host="localhost",
        database="analytics",
        username="postgres",
        password="secret",
    )


def test_postgresql_mcp_execute_read_only_returns_success_payload(monkeypatch) -> None:
    cursor = MagicMock()
    cursor.description = [("id",), ("name",)]
    cursor.fetchall.return_value = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]

    connection = MagicMock()
    connection.cursor.return_value = cursor
    monkeypatch.setattr(psycopg2, "connect", lambda **_: connection)

    repository = _build_repository()
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="postgresql",
            database_id="db-main",
            sql="SELECT id, name FROM users ORDER BY id",
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert response.result.columns == ["id", "name"]
    assert response.result.row_count == 2
    assert response.result.rows[0]["name"] == "Alice"


def test_postgresql_mcp_execute_read_only_applies_row_limit(monkeypatch) -> None:
    cursor = MagicMock()
    cursor.description = [("id",), ("name",)]
    cursor.fetchmany.return_value = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Carol"},
    ]

    connection = MagicMock()
    connection.cursor.return_value = cursor
    monkeypatch.setattr(psycopg2, "connect", lambda **_: connection)

    repository = _build_repository()
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="postgresql",
            database_id="db-main",
            sql="SELECT id, name FROM users ORDER BY id",
            row_limit=2,
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert response.result.row_count == 2
    assert response.result.truncated is True


def test_postgresql_mcp_execute_read_only_rejects_non_read_only_sql() -> None:
    repository = _build_repository()
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="postgresql",
            database_id="db-main",
            sql="DELETE FROM users",
            meta=_meta(),
        )
    )

    assert response.status == "error"
    assert response.error.code == "forbidden_operation"


def test_postgresql_mcp_fetch_schema_returns_tables_and_columns(monkeypatch) -> None:
    cursor = MagicMock()
    cursor.fetchall.side_effect = [
        [
            {"table_schema": "public", "table_name": "users", "table_type": "BASE TABLE"},
            {"table_schema": "public", "table_name": "user_names", "table_type": "VIEW"},
        ],
        [
            {"column_name": "id", "data_type": "integer", "is_nullable": "NO"},
            {"column_name": "name", "data_type": "text", "is_nullable": "YES"},
        ],
        [
            {"column_name": "name", "data_type": "text", "is_nullable": "YES"},
        ],
    ]

    connection = MagicMock()
    connection.cursor.return_value = cursor
    monkeypatch.setattr(psycopg2, "connect", lambda **_: connection)

    repository = _build_repository()
    response = repository.fetch_schema(
        MCPSchemaRequest(
            dialect="postgresql",
            database_id="db-main",
            include_views=True,
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert len(response.result.tables) == 2
    assert response.result.tables[0].name == "users"
    assert response.result.tables[0].schema_name == "public"
    assert response.result.tables[0].table_type == "TABLE"
    assert response.result.tables[0].columns[0].nullable is False
    assert response.result.tables[1].table_type == "VIEW"


def test_postgresql_mcp_check_health_returns_success(monkeypatch) -> None:
    cursor = MagicMock()
    cursor.fetchone.return_value = ("PostgreSQL 16.3",)

    connection = MagicMock()
    connection.cursor.return_value = cursor
    monkeypatch.setattr(psycopg2, "connect", lambda **_: connection)

    repository = _build_repository()
    response = repository.check_health(
        MCPHealthRequest(
            dialect="postgresql",
            database_id="db-main",
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert response.result.reachable is True
    assert response.result.server_version == "PostgreSQL 16.3"


def test_postgresql_mcp_returns_unsupported_dialect_error() -> None:
    repository = _build_repository()
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="sqlite",
            database_id="db-main",
            sql="SELECT 1",
            meta=_meta(),
        )
    )

    assert response.status == "error"
    assert response.error.code == "unsupported_dialect"
