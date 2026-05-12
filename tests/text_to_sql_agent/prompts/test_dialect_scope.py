"""Tests for SQL dialect prompt scope matrix."""

import pytest

from text_to_sql_agent.prompts.dialect_scope import (
    DIALECT_SCOPE_MATRIX,
    get_dialect_prompt_scope,
    list_supported_dialects,
)


def test_supported_dialects_are_complete() -> None:
    assert set(DIALECT_SCOPE_MATRIX) == {"postgresql", "mysql", "athena", "sqlite"}
    assert list_supported_dialects() == ("athena", "mysql", "postgresql", "sqlite")


def test_scope_entries_have_prompt_requirements_and_examples() -> None:
    for dialect, scope in DIALECT_SCOPE_MATRIX.items():
        assert scope.name == dialect
        assert len(scope.prompt_requirements) >= 3
        assert len(scope.examples) >= 2
        assert scope.limit_syntax == "LIMIT {n}"


def test_examples_are_read_only_select_statements() -> None:
    forbidden_tokens = ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE ")

    for scope in DIALECT_SCOPE_MATRIX.values():
        for statement in scope.examples:
            normalized = statement.upper()
            assert normalized.startswith(("SELECT ", "WITH "))
            assert all(token not in normalized for token in forbidden_tokens)


def test_get_dialect_prompt_scope_is_case_insensitive() -> None:
    scope = get_dialect_prompt_scope("PostgreSQL")
    assert scope.name == "postgresql"


def test_get_dialect_prompt_scope_rejects_unsupported_dialect() -> None:
    with pytest.raises(ValueError, match="Unsupported dialect"):
        get_dialect_prompt_scope("sqlserver")
