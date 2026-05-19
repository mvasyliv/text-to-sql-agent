"""SQLite query execution repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from .query_execution_repository import QueryExecutionRepository


class SQLiteQueryExecutionRepository(QueryExecutionRepository):
    """Execute read-only SQL against SQLite and return normalized result payload."""

    def execute_read_only(
        self,
        database_id: str,
        sql_query: str,
        connection_config: dict[str, Any],
    ) -> dict[str, Any]:
        db_path = connection_config.get("path")
        if not db_path:
            raise ValueError("SQLite connection_config must include 'path'")

        conn = sqlite3.connect(str(db_path))
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(sql_query)
            rows = [dict(row) for row in cur.fetchall()]
            columns = [col[0] for col in (cur.description or [])]
            return {
                "database_id": database_id,
                "rows": rows,
                "columns": columns,
                "row_count": len(rows),
            }
        finally:
            conn.close()
