"""Factory for query execution repositories by SQL dialect."""

from __future__ import annotations

from .provider_factory import normalize_dialect
from .query_execution_repository import QueryExecutionRepository
from .sqlite_query_execution_repository import SQLiteQueryExecutionRepository


def get_query_execution_repository(dialect: str) -> QueryExecutionRepository:
    """Return a query execution repository for the given SQL dialect."""
    normalized = normalize_dialect(dialect)
    if normalized == "sqlite":
        return SQLiteQueryExecutionRepository()

    raise NotImplementedError(
        f"Query execution repository for dialect '{normalized}' is not implemented"
    )
