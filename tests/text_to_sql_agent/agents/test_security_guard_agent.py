"""Tests for security guard agent (T-2026-05-18-045)."""

from text_to_sql_agent.agents.security_guard_agent import (
    build_security_guard_node,
    validate_sql_security,
)


class TestValidateSqlSecurity:
    def test_allows_count_without_limit(self):
        result = validate_sql_security("SELECT COUNT(*) FROM users")
        assert result.approved is True
        assert result.violations == []

    def test_allows_select_with_limit(self):
        result = validate_sql_security("SELECT * FROM users LIMIT 10")
        assert result.approved is True

    def test_blocks_non_read_only_entrypoint(self):
        result = validate_sql_security("EXPLAIN SELECT * FROM users")
        assert result.approved is False
        assert "non_read_only_entrypoint" in result.violations

    def test_blocks_dml(self):
        result = validate_sql_security("DELETE FROM users WHERE id = 1")
        assert result.approved is False
        assert "delete" in result.violations

    def test_allows_select_without_limit(self):
        result = validate_sql_security("SELECT * FROM users")
        assert result.approved is True
        assert result.violations == []

    def test_blocks_inline_comment_pattern(self):
        result = validate_sql_security("SELECT * FROM users LIMIT 10 -- test")
        assert result.approved is False
        assert "inline_comment" in result.violations

    def test_blocks_union_select_pattern(self):
        result = validate_sql_security("SELECT id FROM users UNION SELECT id FROM admins")
        assert result.approved is False
        assert "union_select" in result.violations

    def test_empty_sql_is_rejected(self):
        result = validate_sql_security("   ")
        assert result.approved is False
        assert result.violations == ["empty_sql"]


class TestBuildSecurityGuardNode:
    def test_node_success(self):
        node = build_security_guard_node()
        state = {"generated_sql": "SELECT * FROM users LIMIT 10"}
        result = node(state)

        assert result["security_approved"] is True
        assert result["security_violations"] == []
        assert result["status"] == "awaiting_approval"

    def test_node_uses_edited_sql(self):
        node = build_security_guard_node()
        state = {
            "generated_sql": "SELECT * FROM users LIMIT 10",
            "edited_sql": "DELETE FROM users WHERE id = 1",
        }
        result = node(state)

        assert result["security_approved"] is False
        assert "delete" in result["security_violations"]

    def test_node_failure(self):
        node = build_security_guard_node()
        result = node({"generated_sql": 42})

        assert result["security_approved"] is False
        assert result["status"] == "failed"
        assert "SQL must be a string" in result["security_violations"][0]
