"""Factory and registry for schema introspection providers."""

from __future__ import annotations

from collections.abc import Mapping

from .introspection_provider import SchemaIntrospectionProvider
from .postgresql_provider import PostgresIntrospectionProvider
from .sqlite_provider import SQLiteIntrospectionProvider

PROVIDER_REGISTRY: dict[str, type[SchemaIntrospectionProvider]] = {
    "postgresql": PostgresIntrospectionProvider,
    "sqlite": SQLiteIntrospectionProvider,
}

_DIALECT_ALIASES: Mapping[str, str] = {
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "sqlite": "sqlite",
    "sqlite3": "sqlite",
}


def normalize_dialect(dialect: str) -> str:
    """Normalize a dialect string to the registry key."""
    normalized = dialect.strip().lower()
    try:
        return _DIALECT_ALIASES[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(
            f"Unsupported dialect '{dialect}'. Supported dialects: {supported}"
        ) from exc


def get_introspection_provider(dialect: str) -> SchemaIntrospectionProvider:
    """Return a concrete schema introspection provider for the dialect."""
    normalized_dialect = normalize_dialect(dialect)
    provider_class = PROVIDER_REGISTRY[normalized_dialect]
    return provider_class()