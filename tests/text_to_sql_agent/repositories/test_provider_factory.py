"""Tests for introspection provider factory and registry (T-2026-05-15-027)."""

import pytest

from text_to_sql_agent.repositories import (
    PROVIDER_REGISTRY,
    PostgresIntrospectionProvider,
    SQLiteIntrospectionProvider,
    get_introspection_provider,
    normalize_dialect,
)


def test_provider_registry_contains_supported_dialects() -> None:
    """Registry should expose the supported provider classes by dialect."""
    assert PROVIDER_REGISTRY["sqlite"] is SQLiteIntrospectionProvider
    assert PROVIDER_REGISTRY["postgresql"] is PostgresIntrospectionProvider


@pytest.mark.parametrize(
    ("dialect", "expected"),
    [
        ("sqlite", "sqlite"),
        ("SQLite", "sqlite"),
        (" sqlite3 ", "sqlite"),
        ("postgres", "postgresql"),
        ("PostgreSQL", "postgresql"),
    ],
)
def test_normalize_dialect_handles_aliases_and_case(
    dialect: str,
    expected: str,
) -> None:
    """Normalization should handle aliases, whitespace, and case."""
    assert normalize_dialect(dialect) == expected


def test_normalize_dialect_raises_for_unsupported_dialect() -> None:
    """Unknown dialects should fail with a helpful error."""
    with pytest.raises(ValueError) as exc_info:
        normalize_dialect("oracle")

    message = str(exc_info.value)
    assert "oracle" in message
    assert "postgresql" in message
    assert "sqlite" in message


def test_get_introspection_provider_returns_sqlite_provider() -> None:
    """Factory should create a SQLite provider for sqlite dialect."""
    provider = get_introspection_provider("sqlite")
    assert isinstance(provider, SQLiteIntrospectionProvider)


def test_get_introspection_provider_returns_postgres_provider_for_alias() -> None:
    """Factory should resolve postgres alias to the PostgreSQL provider."""
    provider = get_introspection_provider("postgres")
    assert isinstance(provider, PostgresIntrospectionProvider)


def test_get_introspection_provider_returns_new_instance_each_time() -> None:
    """Factory should not reuse provider instances across calls."""
    first = get_introspection_provider("sqlite")
    second = get_introspection_provider("sqlite")

    assert isinstance(first, SQLiteIntrospectionProvider)
    assert isinstance(second, SQLiteIntrospectionProvider)
    assert first is not second


def test_get_introspection_provider_raises_for_unsupported_dialect() -> None:
    """Factory should raise for unsupported dialects."""
    with pytest.raises(ValueError) as exc_info:
        get_introspection_provider("mysql")

    assert "mysql" in str(exc_info.value)