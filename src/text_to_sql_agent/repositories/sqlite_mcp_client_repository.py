"""SQLite implementation of the MCP client repository contract."""

from __future__ import annotations

import sqlite3
from time import perf_counter

from text_to_sql_agent.models import (
    MCPExecuteRequest,
    MCPExecuteSuccessPayload,
    MCPHealthRequest,
    MCPHealthSuccessPayload,
    MCPSchemaColumn,
    MCPSchemaRequest,
    MCPSchemaSuccessPayload,
    MCPSchemaTable,
    MCPToolError,
    MCPToolErrorResponse,
    MCPToolRequestMeta,
    MCPToolResponse,
    MCPToolSuccessResponse,
)

from .mcp_client_repository import MCPClientRepository

_READ_ONLY_PREFIXES = ("select", "with", "explain")


class SQLiteMCPClientRepository(MCPClientRepository):
    """Concrete MCP adapter for SQLite-backed execution and schema access."""

    def __init__(self, database_path: str) -> None:
        normalized_path = database_path.strip()
        if not normalized_path:
            raise ValueError("SQLite MCP adapter requires a non-empty database path")
        self._database_path = normalized_path

    def execute_tool(
        self,
        request: MCPExecuteRequest | MCPSchemaRequest | MCPHealthRequest,
    ) -> MCPToolResponse:
        if isinstance(request, MCPExecuteRequest):
            return self.execute_read_only(request)
        if isinstance(request, MCPSchemaRequest):
            return self.fetch_schema(request)
        return self.check_health(request)

    def execute_read_only(self, request: MCPExecuteRequest) -> MCPToolResponse:
        if request.dialect != "sqlite":
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="unsupported_dialect",
                message=f"SQLite MCP adapter does not support dialect '{request.dialect}'",
            )

        sql_query = request.sql.strip()
        if not sql_query:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="invalid_request",
                message="SQL query is empty",
            )

        first_token = sql_query.lower().lstrip("(")
        if not any(first_token.startswith(prefix) for prefix in _READ_ONLY_PREFIXES):
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="forbidden_operation",
                message="Only read-only SQL statements are allowed",
            )

        started_at = perf_counter()
        try:
            with sqlite3.connect(self._database_path) as connection:
                connection.row_factory = sqlite3.Row
                cursor = connection.cursor()
                cursor.execute(sql_query, request.parameters)
                columns = [col[0] for col in (cursor.description or [])]

                if request.row_limit is None:
                    raw_rows = cursor.fetchall()
                    truncated = False
                else:
                    raw_rows = cursor.fetchmany(request.row_limit + 1)
                    truncated = len(raw_rows) > request.row_limit
                    if truncated:
                        raw_rows = raw_rows[: request.row_limit]

                rows = [dict(row) for row in raw_rows]
        except sqlite3.Error as exc:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="execution_failed",
                message=str(exc),
                details={"database_path": self._database_path},
            )

        elapsed_ms = int((perf_counter() - started_at) * 1000)
        return MCPToolSuccessResponse(
            tool_name=request.tool_name,
            meta=request.meta,
            result=MCPExecuteSuccessPayload(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                elapsed_ms=elapsed_ms,
            ),
        )

    def fetch_schema(self, request: MCPSchemaRequest) -> MCPToolResponse:
        if request.dialect != "sqlite":
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="unsupported_dialect",
                message=f"SQLite MCP adapter does not support dialect '{request.dialect}'",
            )

        try:
            with sqlite3.connect(self._database_path) as connection:
                connection.row_factory = sqlite3.Row
                cursor = connection.cursor()
                table_types = ["table"]
                if request.include_views:
                    table_types.append("view")

                placeholders = ", ".join("?" for _ in table_types)
                cursor.execute(
                    f"SELECT name, type FROM sqlite_master WHERE type IN ({placeholders}) ORDER BY name",
                    table_types,
                )
                catalog_rows = cursor.fetchall()

                requested_tables = set(request.table_names or [])
                tables: list[MCPSchemaTable] = []
                for row in catalog_rows:
                    table_name = str(row["name"])
                    if requested_tables and table_name not in requested_tables:
                        continue

                    pragma_name = table_name.replace('"', '""')
                    column_cursor = connection.cursor()
                    column_cursor.execute(f'PRAGMA table_info("{pragma_name}")')
                    columns = [
                        MCPSchemaColumn(
                            name=str(column_row[1]),
                            data_type=str(column_row[2]),
                            nullable=not bool(column_row[3]),
                        )
                        for column_row in column_cursor.fetchall()
                    ]
                    table_type = "VIEW" if str(row["type"]).lower() == "view" else "TABLE"
                    tables.append(
                        MCPSchemaTable(
                            name=table_name,
                            schema_name=None,
                            table_type=table_type,
                            columns=columns,
                        )
                    )
        except sqlite3.Error as exc:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="execution_failed",
                message=str(exc),
                details={"database_path": self._database_path},
            )

        return MCPToolSuccessResponse(
            tool_name=request.tool_name,
            meta=request.meta,
            result=MCPSchemaSuccessPayload(tables=tables),
        )

    def check_health(self, request: MCPHealthRequest) -> MCPToolResponse:
        if request.dialect != "sqlite":
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="unsupported_dialect",
                message=f"SQLite MCP adapter does not support dialect '{request.dialect}'",
            )

        started_at = perf_counter()
        try:
            with sqlite3.connect(self._database_path) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT sqlite_version()")
                version = cursor.fetchone()
        except sqlite3.Error as exc:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="tool_unavailable",
                message=str(exc),
                details={"database_path": self._database_path},
            )

        elapsed_ms = int((perf_counter() - started_at) * 1000)
        return MCPToolSuccessResponse(
            tool_name=request.tool_name,
            meta=request.meta,
            result=MCPHealthSuccessPayload(
                reachable=True,
                latency_ms=elapsed_ms,
                server_version=str(version[0]) if version else None,
            ),
        )

    def _error_response(
        self,
        *,
        tool_name: str,
        meta: MCPToolRequestMeta,
        code: str,
        message: str,
        details: dict[str, str] | None = None,
    ) -> MCPToolErrorResponse:
        return MCPToolErrorResponse(
            tool_name=tool_name,
            meta=meta,
            error=MCPToolError(
                code=code,
                message=message,
                retriable=False,
                details=details or {},
            ),
        )