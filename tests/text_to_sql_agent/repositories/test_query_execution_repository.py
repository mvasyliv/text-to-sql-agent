"""Tests for query execution repositories (T-2026-05-18-047)."""

import sqlite3

import pytest

from text_to_sql_agent.repositories import (
    SQLiteQueryExecutionRepository,
    get_query_execution_repository,
)


def _seed_db(path: str) -> None:
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        cur.execute("INSERT INTO users (name) VALUES ('Alice')")
        cur.execute("INSERT INTO users (name) VALUES ('Bob')")
        conn.commit()
    finally:
        conn.close()


def test_sqlite_query_execution_repository_returns_normalized_payload(tmp_path):
    db_path = tmp_path / "test_exec.db"
    _seed_db(str(db_path))

    repo = SQLiteQueryExecutionRepository()
    result = repo.execute_read_only(
        database_id="testdb",
        sql_query="SELECT id, name FROM users ORDER BY id",
        connection_config={"path": str(db_path)},
    )

    assert result["database_id"] == "testdb"
    assert result["columns"] == ["id", "name"]
    assert result["row_count"] == 2
    assert result["rows"][0]["name"] == "Alice"


def test_sqlite_query_execution_requires_path():
    repo = SQLiteQueryExecutionRepository()
    with pytest.raises(ValueError):
        repo.execute_read_only("db", "SELECT 1", {})


def test_get_query_execution_repository_sqlite():
    repo = get_query_execution_repository("sqlite")
    assert isinstance(repo, SQLiteQueryExecutionRepository)


def test_get_query_execution_repository_not_implemented_for_postgres_alias():
    with pytest.raises(NotImplementedError):
        get_query_execution_repository("postgres")
