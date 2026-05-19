"""Tests for syntax validator agent (T-2026-05-18-044)."""

from text_to_sql_agent.agents.syntax_validator_agent import (
    build_syntax_validator_node,
    validate_sql_syntax,
)


class TestValidateSqlSyntax:
    def test_valid_select(self):
        result = validate_sql_syntax("SELECT * FROM users LIMIT 10")
        assert result.valid is True
        assert result.errors == []

    def test_valid_with_cte(self):
        result = validate_sql_syntax(
            "WITH base AS (SELECT id FROM users) SELECT * FROM base"
        )
        assert result.valid is True

    def test_empty_sql_invalid(self):
        result = validate_sql_syntax("   ")
        assert result.valid is False
        assert "SQL is empty" in result.errors

    def test_multiple_statements_invalid(self):
        result = validate_sql_syntax("SELECT 1; SELECT 2;")
        assert result.valid is False
        assert "Only a single SQL statement is allowed" in result.errors

    def test_disallowed_operation_invalid(self):
        result = validate_sql_syntax("UPDATE users SET name = 'x'")
        assert result.valid is False
        assert "Disallowed operation detected: UPDATE" in result.errors

    def test_unbalanced_parentheses_invalid(self):
        result = validate_sql_syntax("SELECT (id FROM users")
        assert result.valid is False
        assert "Unbalanced parentheses detected" in result.errors

    def test_unbalanced_single_quotes_invalid(self):
        result = validate_sql_syntax("SELECT * FROM users WHERE name = 'Alice")
        assert result.valid is False
        assert "Unbalanced single quotes detected" in result.errors


class TestBuildSyntaxValidatorNode:
    def test_node_success(self):
        node = build_syntax_validator_node()
        state = {"generated_sql": "SELECT * FROM users"}
        result = node(state)

        assert result["syntax_valid"] is True
        assert result["syntax_errors"] == []
        assert result["status"] == "validating"

    def test_node_uses_edited_sql_if_present(self):
        node = build_syntax_validator_node()
        state = {
            "generated_sql": "SELECT * FROM users",
            "edited_sql": "SELECT * FROM users LIMIT 5",
        }
        result = node(state)
        assert result["syntax_valid"] is True

    def test_node_failure(self):
        node = build_syntax_validator_node()
        state = {"generated_sql": 123}
        result = node(state)

        assert result["syntax_valid"] is False
        assert result["status"] == "failed"
        assert "SQL must be a string" in result["syntax_errors"][0]
