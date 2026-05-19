"""Tests for query execution agent (T-2026-05-18-047)."""

import sqlite3

from text_to_sql_agent.agents.query_execution_agent import (
    build_query_execution_node,
    execute_approved_query,
    is_read_only_query,
)


def _seed_db(path: str) -> None:
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, title TEXT)")
        cur.execute("INSERT INTO events (title) VALUES ('Launch')")
        conn.commit()
    finally:
        conn.close()


def test_is_read_only_query():
    assert is_read_only_query("SELECT * FROM events") is True
    assert is_read_only_query("WITH cte AS (SELECT 1) SELECT * FROM cte") is True
    assert is_read_only_query("DELETE FROM events") is False


def test_execute_approved_query_sqlite(tmp_path):
    db_path = tmp_path / "agent_exec.db"
    _seed_db(str(db_path))

    result = execute_approved_query(
        database_id="db1",
        dialect="sqlite",
        sql_query="SELECT id, title FROM events LIMIT 10",
        connection_config={"path": str(db_path)},
    )

    assert result["database_id"] == "db1"
    assert result["dialect"] == "sqlite"
    assert result["row_count"] == 1
    assert result["rows"][0]["title"] == "Launch"


def test_execute_approved_query_rejects_non_read_only(tmp_path):
    db_path = tmp_path / "agent_exec_ro.db"
    _seed_db(str(db_path))

    try:
        execute_approved_query(
            database_id="db1",
            dialect="sqlite",
            sql_query="DELETE FROM events",
            connection_config={"path": str(db_path)},
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "read-only" in str(exc)


def test_build_query_execution_node_stub_mode_without_config():
    node = build_query_execution_node(None)
    result = node(
        {
            "database_id": "db1",
            "dialect": "sqlite",
            "generated_sql": "SELECT * FROM events",
            "edited_sql": None,
        }
    )

    assert result["execution_error"] is None
    assert result["execution_result"]["metadata"]["mode"] == "stub"
    assert result["status"] == "post_processing"


def test_build_query_execution_node_real_mode(tmp_path):
    db_path = tmp_path / "agent_exec_node.db"
    _seed_db(str(db_path))

    node = build_query_execution_node({"path": str(db_path)})
    result = node(
        {
            "database_id": "db1",
            "dialect": "sqlite",
            "generated_sql": "SELECT * FROM events LIMIT 5",
            "edited_sql": None,
        }
    )

    assert result["execution_error"] is None
    assert result["execution_result"]["row_count"] == 1
    assert result["status"] == "post_processing"


def test_build_query_execution_node_failure_on_invalid_sql():
    node = build_query_execution_node({"path": "/tmp/does-not-matter.db"})
    result = node(
        {
            "database_id": "db1",
            "dialect": "sqlite",
            "generated_sql": "DELETE FROM events",
            "edited_sql": None,
        }
    )

    assert result["execution_result"] is None
    assert result["status"] == "failed"
    assert "read-only" in result["execution_error"]
