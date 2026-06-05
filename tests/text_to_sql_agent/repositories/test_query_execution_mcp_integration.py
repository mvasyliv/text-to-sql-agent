"""Integration tests for multi-dialect MCP query execution."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import psycopg2
import pytest

from text_to_sql_agent.models import MCPExecuteRequest, MCPToolRequestMeta
from text_to_sql_agent.repositories import get_query_execution_repository


def _seed_sqlite_db(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.executemany(
            "INSERT INTO users (name) VALUES (?)",
            [("Alice",), ("Bob",), ("Carol",)],
        )
        connection.commit()
    finally:
        connection.close()


def _request_meta() -> MCPToolRequestMeta:
    return MCPToolRequestMeta(request_id="req-001", user_id="u-001", conversation_id="c-001")


def test_sqlite_query_execution_integration_returns_success_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite_integration.db"
    _seed_sqlite_db(db_path)

    repository = get_query_execution_repository(
        "sqlite",
        {
            "path": str(db_path),
            "timeout_ms": 5000,
            "row_limit": 2,
        },
    )

    result = repository.execute_read_only(
        "testdb",
        "SELECT id, name FROM users ORDER BY id",
        {
            "path": str(db_path),
            "timeout_ms": 5000,
            "row_limit": 2,
        },
    )

    assert result["database_id"] == "testdb"
    assert result["columns"] == ["id", "name"]
    assert result["row_count"] == 2
    assert result["truncated"] is True
    assert result["rows"][0]["name"] == "Alice"
    assert isinstance(result["elapsed_ms"], int)


def test_sqlite_query_execution_integration_returns_denied_error_shape(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite_integration.db"
    _seed_sqlite_db(db_path)

    repository = get_query_execution_repository("sqlite", {"path": str(db_path)})
    response = repository._mcp_repository.execute_read_only(  # type: ignore[attr-defined]
        MCPExecuteRequest(
            dialect="sqlite",
            database_id="db-main",
            sql="DELETE FROM users",
            meta=_request_meta(),
        )
    )

    assert response.status == "error"
    assert response.error.code == "forbidden_operation"
    assert response.error.retriable is False
    assert response.error.details == {}


def test_postgresql_query_execution_integration_propagates_timeout_and_returns_success_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = MagicMock()
    cursor.description = [("id",), ("name",)]
    cursor.fetchmany.return_value = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Carol"},
    ]

    connection = MagicMock()
    connection.cursor.return_value = cursor
    connect_mock = MagicMock(return_value=connection)
    monkeypatch.setattr(psycopg2, "connect", connect_mock)

    repository = get_query_execution_repository(
        "postgresql",
        {
            "host": "localhost",
            "database": "analytics",
            "username": "postgres",
            "password": "secret",
            "timeout_ms": 4500,
            "row_limit": 2,
        },
    )

    result = repository.execute_read_only(
        "db-main",
        "SELECT id, name FROM users ORDER BY id",
        {
            "host": "localhost",
            "database": "analytics",
            "username": "postgres",
            "password": "secret",
            "timeout_ms": 4500,
            "row_limit": 2,
        },
    )

    assert result["columns"] == ["id", "name"]
    assert result["row_count"] == 2
    assert result["truncated"] is True
    assert connect_mock.call_count == 1
    assert connect_mock.call_args.kwargs["connect_timeout"] == 4


def test_postgresql_query_execution_integration_returns_denied_error_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect_mock = MagicMock()
    monkeypatch.setattr(psycopg2, "connect", connect_mock)

    repository = get_query_execution_repository(
        "postgresql",
        {
            "host": "localhost",
            "database": "analytics",
            "username": "postgres",
            "password": "secret",
        },
    )

    response = repository._mcp_repository.execute_read_only(  # type: ignore[attr-defined]
        MCPExecuteRequest(
            dialect="postgresql",
            database_id="db-main",
            sql="DELETE FROM users",
            meta=_request_meta(),
        )
    )

    assert response.status == "error"
    assert response.error.code == "forbidden_operation"
    assert response.error.retriable is False
    assert response.error.details == {}
    assert connect_mock.call_count == 0


def test_athena_query_execution_integration_propagates_timeout_and_returns_success_payload() -> None:
    captured: dict[str, object] = {}

    def invoker(tool_name: str, payload: dict[str, object], timeout_ms: int) -> dict[str, object]:
        captured["tool_name"] = tool_name
        captured["payload"] = payload
        captured["timeout_ms"] = timeout_ms
        return {
            "columns": ["id", "name"],
            "rows": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Carol"},
            ],
            "elapsed_ms": 19,
        }

    repository = get_query_execution_repository(
        "athena",
        {
            "endpoint": "mcp://athena-adapter",
            "catalog": "AwsDataCatalog",
            "database": "analytics",
            "workgroup": "primary",
            "timeout_ms": 4500,
            "mcp_invoker": invoker,
        },
    )

    result = repository.execute_read_only(
        "db-main",
        "SELECT id, name FROM users ORDER BY id",
        {
            "endpoint": "mcp://athena-adapter",
            "catalog": "AwsDataCatalog",
            "database": "analytics",
            "workgroup": "primary",
            "timeout_ms": 4500,
            "row_limit": 2,
            "mcp_invoker": invoker,
        },
    )

    assert result["columns"] == ["id", "name"]
    assert result["row_count"] == 2
    assert result["truncated"] is True
    assert captured["tool_name"] == "mcp.db.execute"
    assert captured["timeout_ms"] == 4500
    assert captured["payload"]["row_limit"] == 2


def test_athena_query_execution_integration_returns_denied_and_timeout_error_shapes() -> None:
    connect_calls: list[tuple[str, dict[str, object], int]] = []

    def denied_invoker(tool_name: str, payload: dict[str, object], timeout_ms: int) -> dict[str, object]:
        connect_calls.append((tool_name, payload, timeout_ms))
        raise AssertionError("denied query should not reach invoker")

    denied_repository = get_query_execution_repository(
        "athena",
        {
            "endpoint": "mcp://athena-adapter",
            "catalog": "AwsDataCatalog",
            "database": "analytics",
            "workgroup": "primary",
            "mcp_invoker": denied_invoker,
        },
    )

    denied_response = denied_repository._mcp_repository.execute_read_only(  # type: ignore[attr-defined]
        MCPExecuteRequest(
            dialect="athena",
            database_id="db-main",
            sql="DELETE FROM users",
            meta=_request_meta(),
        )
    )

    assert denied_response.status == "error"
    assert denied_response.error.code == "forbidden_operation"
    assert denied_response.error.retriable is False
    assert denied_response.error.details == {}
    assert connect_calls == []

    def timeout_invoker(_tool_name: str, _payload: dict[str, object], _timeout_ms: int) -> dict[str, object]:
        raise TimeoutError("Athena MCP timed out")

    timeout_repository = get_query_execution_repository(
        "athena",
        {
            "endpoint": "mcp://athena-adapter",
            "catalog": "AwsDataCatalog",
            "database": "analytics",
            "workgroup": "primary",
            "timeout_ms": 4500,
            "mcp_invoker": timeout_invoker,
        },
    )

    timeout_response = timeout_repository._mcp_repository.execute_read_only(  # type: ignore[attr-defined]
        MCPExecuteRequest(
            dialect="athena",
            database_id="db-main",
            sql="SELECT id FROM users",
            timeout_ms=4500,
            meta=_request_meta(),
        )
    )

    assert timeout_response.status == "error"
    assert timeout_response.error.code == "timeout"
    assert timeout_response.error.retriable is True
    assert timeout_response.error.details == {
        "endpoint": "mcp://athena-adapter",
        "catalog": "AwsDataCatalog",
        "database": "analytics",
        "workgroup": "primary",
    }
