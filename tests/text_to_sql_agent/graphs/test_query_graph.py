"""Tests for the DB query orchestration graph (T-2026-05-18-041).

Tests cover:
- Graph compiles without error.
- Happy path: schema → sql → syntax OK → security OK → approval → execution → done.
- Security guard blocks dangerous SQL.
- Syntax validator rejects empty SQL.
- Human rejection leads to cancelled status.
- Human can edit SQL before approval.
"""

import pytest
from langgraph.types import Command

from text_to_sql_agent.graphs.query_graph import (
    QueryState,
    build_query_graph,
    node_security_guard,
    node_syntax_validator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _initial_state(question: str = "How many users?") -> dict:
    return {
        "user_id": "u-001",
        "conversation_id": "c-001",
        "message_id": "m-001",
        "user_question": question,
        "database_id": "testdb",
        "dialect": "sqlite",
        "schema_context": None,
        "generated_sql": None,
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


def _thread(thread_id: str = "t-001") -> dict:
    return {"configurable": {"thread_id": thread_id}}


# ---------------------------------------------------------------------------
# Unit tests for individual nodes
# ---------------------------------------------------------------------------


class TestSyntaxValidator:
    def test_valid_sql(self):
        state = {**_initial_state(), "generated_sql": "SELECT * FROM users"}
        result = node_syntax_validator(state)
        assert result["syntax_valid"] is True
        assert result["syntax_errors"] == []

    def test_empty_sql_is_invalid(self):
        state = {**_initial_state(), "generated_sql": ""}
        result = node_syntax_validator(state)
        assert result["syntax_valid"] is False
        assert len(result["syntax_errors"]) > 0

    def test_none_sql_is_invalid(self):
        state = {**_initial_state(), "generated_sql": None}
        result = node_syntax_validator(state)
        assert result["syntax_valid"] is False


class TestSecurityGuard:
    def test_select_is_approved(self):
        state = {**_initial_state(), "generated_sql": "SELECT * FROM users"}
        result = node_security_guard(state)
        assert result["security_approved"] is True
        assert result["security_violations"] == []

    def test_drop_is_blocked(self):
        state = {**_initial_state(), "generated_sql": "DROP TABLE users"}
        result = node_security_guard(state)
        assert result["security_approved"] is False
        assert "drop" in result["security_violations"]

    def test_delete_is_blocked(self):
        state = {**_initial_state(), "generated_sql": "DELETE FROM users WHERE 1=1"}
        result = node_security_guard(state)
        assert result["security_approved"] is False
        assert "delete" in result["security_violations"]


# ---------------------------------------------------------------------------
# Integration tests for the full graph
# ---------------------------------------------------------------------------


class TestQueryGraph:
    def test_graph_compiles(self):
        graph = build_query_graph()
        assert graph is not None

    def test_happy_path_pauses_at_human_approval(self):
        """Graph should run up to interrupt before human_approval node."""
        graph = build_query_graph()
        config = _thread("happy-1")
        result = graph.invoke(_initial_state("How many users?"), config)
        # Graph pauses at interrupt — status should not yet be 'done'
        assert result["status"] != "done"
        assert result["generated_sql"] is not None
        assert result["syntax_valid"] is True
        assert result["security_approved"] is True

    def test_human_approves_leads_to_done(self):
        graph = build_query_graph()
        config = _thread("happy-2")
        graph.invoke(_initial_state("How many users?"), config)
        # Resume with approval
        result = graph.invoke(Command(resume="approve"), config)
        assert result["status"] == "done"
        assert result["human_approved"] is True
        assert result["execution_result"] is not None
        assert result["chart_spec"] is not None
        assert result["export_path"] is not None

    def test_human_rejects_leads_to_cancelled(self):
        graph = build_query_graph()
        config = _thread("reject-1")
        graph.invoke(_initial_state("Count rows"), config)
        result = graph.invoke(Command(resume="reject"), config)
        assert result["status"] in {"failed", "cancelled"}
        assert result["human_approved"] is False

    def test_human_edits_sql(self):
        graph = build_query_graph()
        config = _thread("edit-1")
        graph.invoke(_initial_state("Show all users"), config)
        result = graph.invoke(
            Command(resume={"edit": "SELECT id, name FROM users LIMIT 10"}),
            config,
        )
        assert result["status"] == "done"
        assert result["edited_sql"] == "SELECT id, name FROM users LIMIT 10"

    def test_log_messages_accumulated(self):
        graph = build_query_graph()
        config = _thread("log-1")
        graph.invoke(_initial_state("Count users"), config)
        result = graph.invoke(Command(resume="approve"), config)
        assert len(result["log_messages"]) > 3
