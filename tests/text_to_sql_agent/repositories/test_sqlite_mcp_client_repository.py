"""Tests for the SQLite MCP client repository."""

import sqlite3

from text_to_sql_agent.models import MCPExecuteRequest, MCPHealthRequest, MCPSchemaRequest, MCPToolRequestMeta
from text_to_sql_agent.repositories import SQLiteMCPClientRepository


def _meta() -> MCPToolRequestMeta:
    return MCPToolRequestMeta(request_id="req-001", user_id="u-001", conversation_id="c-001")


def _seed_db(path: str) -> None:
    connection = sqlite3.connect(path)
    try:
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("CREATE VIEW user_names AS SELECT name FROM users")
        cursor.executemany(
            "INSERT INTO users (name) VALUES (?)",
            [("Alice",), ("Bob",), ("Carol",)],
        )
        connection.commit()
    finally:
        connection.close()


def test_sqlite_mcp_execute_read_only_returns_success_payload(tmp_path) -> None:
    db_path = tmp_path / "sqlite_mcp.db"
    _seed_db(str(db_path))

    repository = SQLiteMCPClientRepository(str(db_path))
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="sqlite",
            database_id="db-main",
            sql="SELECT id, name FROM users ORDER BY id",
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert response.result.columns == ["id", "name"]
    assert response.result.row_count == 3
    assert response.result.rows[0]["name"] == "Alice"


def test_sqlite_mcp_execute_read_only_applies_row_limit(tmp_path) -> None:
    db_path = tmp_path / "sqlite_mcp.db"
    _seed_db(str(db_path))

    repository = SQLiteMCPClientRepository(str(db_path))
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="sqlite",
            database_id="db-main",
            sql="SELECT id, name FROM users ORDER BY id",
            row_limit=2,
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert response.result.row_count == 2
    assert response.result.truncated is True


def test_sqlite_mcp_execute_read_only_rejects_non_read_only_sql(tmp_path) -> None:
    db_path = tmp_path / "sqlite_mcp.db"
    _seed_db(str(db_path))

    repository = SQLiteMCPClientRepository(str(db_path))
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="sqlite",
            database_id="db-main",
            sql="DELETE FROM users",
            meta=_meta(),
        )
    )

    assert response.status == "error"
    assert response.error.code == "forbidden_operation"


def test_sqlite_mcp_fetch_schema_returns_tables_and_views(tmp_path) -> None:
    db_path = tmp_path / "sqlite_mcp.db"
    _seed_db(str(db_path))

    repository = SQLiteMCPClientRepository(str(db_path))
    response = repository.fetch_schema(
        MCPSchemaRequest(
            dialect="sqlite",
            database_id="db-main",
            include_views=True,
            meta=_meta(),
        )
    )

    assert response.status == "success"
    table_names = [table.name for table in response.result.tables]
    assert "users" in table_names
    assert "user_names" in table_names


def test_sqlite_mcp_check_health_returns_success(tmp_path) -> None:
    db_path = tmp_path / "sqlite_mcp.db"
    _seed_db(str(db_path))

    repository = SQLiteMCPClientRepository(str(db_path))
    response = repository.check_health(
        MCPHealthRequest(
            dialect="sqlite",
            database_id="db-main",
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert response.result.reachable is True
    assert response.result.server_version is not None


def test_sqlite_mcp_returns_unsupported_dialect_error(tmp_path) -> None:
    db_path = tmp_path / "sqlite_mcp.db"
    _seed_db(str(db_path))

    repository = SQLiteMCPClientRepository(str(db_path))
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="postgresql",
            database_id="db-main",
            sql="SELECT 1",
            meta=_meta(),
        )
    )

    assert response.status == "error"
    assert response.error.code == "unsupported_dialect"