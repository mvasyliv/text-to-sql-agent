"""Abstract repository contract for SQL query execution backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class QueryExecutionRepository(ABC):
    """Contract for executing read-only SQL against a target database."""

    @abstractmethod
    def execute_read_only(
        self,
        database_id: str,
        sql_query: str,
        connection_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a read-only SQL query and return normalized tabular payload."""
