"""Tests for shared MCP security policy service."""

import pytest

from text_to_sql_agent.services.mcp_security_policy import (
    enforce_mcp_sql_policy,
    validate_mcp_sql_policy,
)


def test_validate_policy_allows_read_only_query() -> None:
    result = validate_mcp_sql_policy("SELECT id, name FROM users")
    assert result.approved is True
    assert result.violations == []


def test_validate_policy_rejects_non_read_only_entrypoint() -> None:
    result = validate_mcp_sql_policy("EXPLAIN SELECT * FROM users")
    assert result.approved is False
    assert "non_read_only_entrypoint" in result.violations


def test_validate_policy_rejects_denied_operation_in_statement() -> None:
    result = validate_mcp_sql_policy("WITH t AS (DELETE FROM users RETURNING id) SELECT * FROM t")
    assert result.approved is False
    assert "denied_operation:delete" in result.violations


def test_validate_policy_enforces_schema_allowlist() -> None:
    result = validate_mcp_sql_policy(
        "SELECT * FROM secret.users",
        allowed_schemas=["public"],
    )
    assert result.approved is False
    assert "schema_not_allowed:secret" in result.violations


def test_enforce_policy_raises_read_only_error() -> None:
    with pytest.raises(ValueError) as exc_info:
        enforce_mcp_sql_policy("DELETE FROM users", {})

    assert "read-only" in str(exc_info.value)


def test_enforce_policy_uses_connection_config_allowlist() -> None:
    with pytest.raises(ValueError) as exc_info:
        enforce_mcp_sql_policy(
            "SELECT * FROM secret.users",
            {"mcp_allowed_schemas": ["public"]},
        )

    assert "schema_not_allowed:secret" in str(exc_info.value)
