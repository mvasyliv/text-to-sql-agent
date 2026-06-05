"""PostgreSQL implementation of the MCP client repository contract."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import psycopg2
import psycopg2.extras

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


class PostgreSQLMCPClientRepository(MCPClientRepository):
    """Concrete MCP adapter for PostgreSQL-backed execution and schema access."""

    def __init__(
        self,
        *,
        host: str,
        database: str,
        username: str,
        password: str,
        port: int = 5432,
        extra_params: dict[str, Any] | None = None,
    ) -> None:
        self._host = host.strip()
        self._database = database.strip()
        self._username = username.strip()
        self._password = password
        self._port = int(port)
        self._extra_params = extra_params or {}

        if not self._host:
            raise ValueError("PostgreSQL MCP adapter requires a non-empty host")
        if not self._database:
            raise ValueError("PostgreSQL MCP adapter requires a non-empty database")
        if not self._username:
            raise ValueError("PostgreSQL MCP adapter requires a non-empty username")
        if not self._password:
            raise ValueError("PostgreSQL MCP adapter requires a non-empty password")

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
        if request.dialect != "postgresql":
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="unsupported_dialect",
                message=(
                    f"PostgreSQL MCP adapter does not support dialect '{request.dialect}'"
                ),
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
        connection = None
        try:
            connection = self._connect(timeout_ms=request.timeout_ms)
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
        except psycopg2.Error as exc:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="execution_failed",
                message=str(exc),
                details={"host": self._host, "database": self._database},
            )
        finally:
            if connection is not None:
                connection.close()

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
        if request.dialect != "postgresql":
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="unsupported_dialect",
                message=(
                    f"PostgreSQL MCP adapter does not support dialect '{request.dialect}'"
                ),
            )

        table_types = ["BASE TABLE"]
        if request.include_views:
            table_types.append("VIEW")

        connection = None
        try:
            connection = self._connect(timeout_ms=30000)
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            catalog_query = """
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND table_type = ANY(%s)
            """
            catalog_params: list[Any] = [table_types]

            if request.schema_names:
                catalog_query += " AND table_schema = ANY(%s)"
                catalog_params.append(request.schema_names)

            if request.table_names:
                catalog_query += " AND table_name = ANY(%s)"
                catalog_params.append(request.table_names)

            catalog_query += " ORDER BY table_schema, table_name"
            cursor.execute(catalog_query, tuple(catalog_params))
            catalog_rows = cursor.fetchall()

            tables: list[MCPSchemaTable] = []
            for row in catalog_rows:
                schema_name = str(row["table_schema"])
                table_name = str(row["table_name"])
                raw_table_type = str(row["table_type"]).upper()
                table_type = "VIEW" if raw_table_type == "VIEW" else "TABLE"

                cursor.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (schema_name, table_name),
                )
                columns = [
                    MCPSchemaColumn(
                        name=str(column_row["column_name"]),
                        data_type=str(column_row["data_type"]),
                        nullable=str(column_row["is_nullable"]).upper() == "YES",
                    )
                    for column_row in cursor.fetchall()
                ]

                tables.append(
                    MCPSchemaTable(
                        name=table_name,
                        schema_name=schema_name,
                        table_type=table_type,
                        columns=columns,
                    )
                )
        except psycopg2.Error as exc:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="execution_failed",
                message=str(exc),
                details={"host": self._host, "database": self._database},
            )
        finally:
            if connection is not None:
                connection.close()

        return MCPToolSuccessResponse(
            tool_name=request.tool_name,
            meta=request.meta,
            result=MCPSchemaSuccessPayload(tables=tables),
        )

    def check_health(self, request: MCPHealthRequest) -> MCPToolResponse:
        if request.dialect != "postgresql":
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="unsupported_dialect",
                message=(
                    f"PostgreSQL MCP adapter does not support dialect '{request.dialect}'"
                ),
            )

        started_at = perf_counter()
        connection = None
        try:
            connection = self._connect(timeout_ms=request.timeout_ms)
            cursor = connection.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()
        except psycopg2.Error as exc:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="tool_unavailable",
                message=str(exc),
                details={"host": self._host, "database": self._database},
            )
        finally:
            if connection is not None:
                connection.close()

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

    def _connect(self, *, timeout_ms: int):
        connect_timeout = max(int(timeout_ms / 1000), 1)
        return psycopg2.connect(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._username,
            password=self._password,
            connect_timeout=connect_timeout,
            **self._extra_params,
        )

    def _error_response(
        self,
        *,
        tool_name: str,
        meta: MCPToolRequestMeta,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
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