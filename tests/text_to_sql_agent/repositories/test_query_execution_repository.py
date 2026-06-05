"""Tests for query execution repositories (T-2026-05-18-047)."""

import sqlite3
from unittest.mock import MagicMock

import pytest

from text_to_sql_agent.repositories import (
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


def test_factory_sqlite_repository_returns_normalized_payload(tmp_path):
    db_path = tmp_path / "test_exec.db"
    _seed_db(str(db_path))

    repo = get_query_execution_repository("sqlite", {"path": str(db_path)})
    result = repo.execute_read_only(
        database_id="testdb",
        sql_query="SELECT id, name FROM users ORDER BY id",
        connection_config={"path": str(db_path)},
    )

    assert result["database_id"] == "testdb"
    assert result["columns"] == ["id", "name"]
    assert result["row_count"] == 2
    assert result["rows"][0]["name"] == "Alice"


def test_factory_sqlite_repository_requires_path():
    with pytest.raises(ValueError):
        get_query_execution_repository("sqlite", {})


def test_get_query_execution_repository_postgres_alias_supported(monkeypatch):
    fake_repo = MagicMock()

    def fake_constructor(**_kwargs):
        return fake_repo

    monkeypatch.setattr(
        "text_to_sql_agent.repositories.query_execution_factory.PostgreSQLMCPClientRepository",
        fake_constructor,
    )

    repo = get_query_execution_repository(
        "postgres",
        {
            "host": "localhost",
            "database": "analytics",
            "username": "postgres",
            "password": "secret",
        },
    )

    assert repo is not None


def test_get_query_execution_repository_athena_supported(monkeypatch):
    fake_repo = MagicMock()

    def fake_constructor(**_kwargs):
        return fake_repo

    monkeypatch.setattr(
        "text_to_sql_agent.repositories.query_execution_factory.AthenaMCPClientRepository",
        fake_constructor,
    )

    repo = get_query_execution_repository(
        "athena",
        {
            "endpoint": "mcp://athena",
            "catalog": "AwsDataCatalog",
            "database": "analytics",
            "workgroup": "primary",
            "mcp_invoker": lambda *_args, **_kwargs: {},
        },
    )

    assert repo is not None
