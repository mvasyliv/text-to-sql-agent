"""Athena implementation of the MCP client repository contract."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

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
MCPInvoker = Callable[[str, dict[str, Any], int], dict[str, Any]]


class AthenaMCPClientRepository(MCPClientRepository):
    """Concrete MCP adapter for Athena-backed execution and schema access."""

    def __init__(
        self,
        *,
        endpoint: str,
        catalog: str,
        database: str,
        workgroup: str,
        timeout_ms: int = 120000,
        invoker: MCPInvoker | None = None,
    ) -> None:
        self._endpoint = endpoint.strip()
        self._catalog = catalog.strip()
        self._database = database.strip()
        self._workgroup = workgroup.strip()
        self._timeout_ms = max(int(timeout_ms), 1)
        self._invoker = invoker

        if not self._endpoint:
            raise ValueError("Athena MCP adapter requires a non-empty endpoint")
        if not self._catalog:
            raise ValueError("Athena MCP adapter requires a non-empty catalog")
        if not self._database:
            raise ValueError("Athena MCP adapter requires a non-empty database")
        if not self._workgroup:
            raise ValueError("Athena MCP adapter requires a non-empty workgroup")

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
        if request.dialect != "athena":
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="unsupported_dialect",
                message=f"Athena MCP adapter does not support dialect '{request.dialect}'",
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
            raw_result = self._invoke_tool(
                tool_name=request.tool_name,
                payload={
                    "dialect": request.dialect,
                    "database_id": request.database_id,
                    "sql": sql_query,
                    "parameters": request.parameters,
                    "row_limit": request.row_limit,
                    "catalog": self._catalog,
                    "database": self._database,
                    "workgroup": self._workgroup,
                },
                timeout_ms=request.timeout_ms,
            )

            raw_rows = list(raw_result.get("rows", []))
            if request.row_limit is None:
                rows = [dict(row) for row in raw_rows]
                truncated = bool(raw_result.get("truncated", False))
            else:
                truncated = len(raw_rows) > request.row_limit
                rows = [dict(row) for row in raw_rows[: request.row_limit]]

            raw_columns = raw_result.get("columns")
            if raw_columns is None:
                columns = list(rows[0].keys()) if rows else []
            else:
                columns = [str(column) for column in raw_columns]

            elapsed_ms = int(raw_result.get("elapsed_ms") or (perf_counter() - started_at) * 1000)
        except TimeoutError as exc:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="timeout",
                message=str(exc),
                retriable=True,
                details=self._error_details(),
            )
        except Exception as exc:  # noqa: BLE001
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="transport_error",
                message=str(exc),
                retriable=True,
                details=self._error_details(),
            )

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
        if request.dialect != "athena":
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="unsupported_dialect",
                message=f"Athena MCP adapter does not support dialect '{request.dialect}'",
            )

        try:
            raw_result = self._invoke_tool(
                tool_name=request.tool_name,
                payload={
                    "dialect": request.dialect,
                    "database_id": request.database_id,
                    "schema_names": request.schema_names,
                    "table_names": request.table_names,
                    "include_views": request.include_views,
                    "catalog": self._catalog,
                    "database": self._database,
                    "workgroup": self._workgroup,
                },
                timeout_ms=self._timeout_ms,
            )

            tables = [
                MCPSchemaTable(
                    name=str(table["name"]),
                    schema_name=(
                        str(table.get("schema_name"))
                        if table.get("schema_name") is not None
                        else None
                    ),
                    table_type=self._normalize_table_type(table.get("table_type")),
                    columns=[
                        MCPSchemaColumn(
                            name=str(column["name"]),
                            data_type=str(column["data_type"]),
                            nullable=bool(column["nullable"]),
                        )
                        for column in table.get("columns", [])
                    ],
                )
                for table in raw_result.get("tables", [])
            ]
        except TimeoutError as exc:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="timeout",
                message=str(exc),
                retriable=True,
                details=self._error_details(),
            )
        except Exception as exc:  # noqa: BLE001
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="transport_error",
                message=str(exc),
                retriable=True,
                details=self._error_details(),
            )

        return MCPToolSuccessResponse(
            tool_name=request.tool_name,
            meta=request.meta,
            result=MCPSchemaSuccessPayload(tables=tables),
        )

    def check_health(self, request: MCPHealthRequest) -> MCPToolResponse:
        if request.dialect != "athena":
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="unsupported_dialect",
                message=f"Athena MCP adapter does not support dialect '{request.dialect}'",
            )

        started_at = perf_counter()
        try:
            raw_result = self._invoke_tool(
                tool_name=request.tool_name,
                payload={
                    "dialect": request.dialect,
                    "database_id": request.database_id,
                    "catalog": self._catalog,
                    "database": self._database,
                    "workgroup": self._workgroup,
                },
                timeout_ms=request.timeout_ms,
            )

            elapsed_ms = int(raw_result.get("latency_ms") or (perf_counter() - started_at) * 1000)
            reachable = bool(raw_result.get("reachable", True))
            server_version = raw_result.get("server_version")
        except TimeoutError as exc:
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="timeout",
                message=str(exc),
                retriable=True,
                details=self._error_details(),
            )
        except Exception as exc:  # noqa: BLE001
            return self._error_response(
                tool_name=request.tool_name,
                meta=request.meta,
                code="tool_unavailable",
                message=str(exc),
                retriable=True,
                details=self._error_details(),
            )

        return MCPToolSuccessResponse(
            tool_name=request.tool_name,
            meta=request.meta,
            result=MCPHealthSuccessPayload(
                reachable=reachable,
                latency_ms=elapsed_ms,
                server_version=str(server_version) if server_version is not None else None,
            ),
        )

    def _invoke_tool(self, tool_name: str, payload: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
        if self._invoker is None:
            raise RuntimeError("Athena MCP invoker is not configured")

        return self._invoker(tool_name, payload, max(int(timeout_ms), 1))

    def _normalize_table_type(self, raw_value: Any) -> str:
        normalized = str(raw_value or "TABLE").upper()
        if normalized in {"TABLE", "VIEW", "MATERIALIZED_VIEW"}:
            return normalized
        return "TABLE"

    def _error_details(self) -> dict[str, Any]:
        return {
            "endpoint": self._endpoint,
            "catalog": self._catalog,
            "database": self._database,
            "workgroup": self._workgroup,
        }

    def _error_response(
        self,
        *,
        tool_name: str,
        meta: MCPToolRequestMeta,
        code: str,
        message: str,
        retriable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> MCPToolErrorResponse:
        return MCPToolErrorResponse(
            tool_name=tool_name,
            meta=meta,
            error=MCPToolError(
                code=code,
                message=message,
                retriable=retriable,
                details=details or {},
            ),
        )
