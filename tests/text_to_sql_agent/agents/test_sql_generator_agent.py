"""Tests for SQL generator agent (T-2026-05-18-043)."""

from text_to_sql_agent.agents.sql_generator_agent import (
    build_sql_generator_node,
    generate_read_only_sql,
)


def _schema_context() -> str:
    return (
        "-- Database: testdb (sqlite)\n\n"
        "TABLE users\n"
        "  id integer [PK]\n"
        "  name text\n\n"
        "TABLE orders\n"
        "  id integer [PK]\n"
        "  user_id integer [FK]"
    )


class TestGenerateReadOnlySql:
    def test_count_intent_uses_count_query(self):
        result = generate_read_only_sql(
            "How many users are there?",
            _schema_context(),
            dialect="sqlite",
        )
        assert result.intent == "count"
        assert "COUNT(*)" in result.sql
        assert 'FROM "users"' in result.sql

    def test_list_intent_uses_limit(self):
        result = generate_read_only_sql(
            "Show all orders",
            _schema_context(),
            max_limit=50,
        )
        assert result.intent == "list"
        assert result.sql.startswith('SELECT * FROM "orders"')
        assert result.sql.endswith("LIMIT 50")

    def test_falls_back_to_first_table_when_not_mentioned(self):
        result = generate_read_only_sql(
            "Give me data",
            _schema_context(),
        )
        assert 'FROM "users"' in result.sql

    def test_no_tables_returns_probe_query(self):
        result = generate_read_only_sql(
            "Show anything",
            "-- No tables found in database 'testdb'",
        )
        assert result.intent == "probe"
        assert result.sql == "SELECT 1 AS result LIMIT 1"

    def test_invalid_limit_raises(self):
        try:
            generate_read_only_sql("Show users", _schema_context(), max_limit=0)
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "max_limit" in str(exc)


class TestBuildSqlGeneratorNode:
    def test_node_populates_generated_sql_and_rationale(self):
        node = build_sql_generator_node(max_limit=25)
        state = {
            "user_question": "Show all users",
            "schema_context": _schema_context(),
            "dialect": "sqlite",
        }
        result = node(state)
        assert result["generated_sql"].startswith('SELECT * FROM "users"')
        assert result["generated_sql"].endswith("LIMIT 25")
        assert result["sql_rationale"]
        assert result["status"] == "validating"

    def test_node_failure_sets_failed_status(self):
        node = build_sql_generator_node(max_limit=-1)
        state = {
            "user_question": "Show all users",
            "schema_context": _schema_context(),
            "dialect": "sqlite",
        }
        result = node(state)
        assert result["generated_sql"] is None
        assert result["status"] == "failed"
        assert "failed to generate SQL" in result["error_message"]
