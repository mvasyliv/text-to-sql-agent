"""Factory for query execution repositories by SQL dialect."""

from __future__ import annotations

from uuid import uuid4

from text_to_sql_agent.models import MCPExecuteRequest, MCPToolRequestMeta

from .athena_mcp_client_repository import AthenaMCPClientRepository
from .mcp_client_repository import MCPClientRepository
from .postgresql_mcp_client_repository import PostgreSQLMCPClientRepository
from .query_execution_repository import QueryExecutionRepository
from .sqlite_mcp_client_repository import SQLiteMCPClientRepository

_EXECUTION_DIALECT_ALIASES = {
    "sqlite": "sqlite",
    "sqlite3": "sqlite",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "postgresql+psycopg2": "postgresql",
    "athena": "athena",
    "awsathena": "athena",
}


class MCPQueryExecutionRepository(QueryExecutionRepository):
    """Query execution repository backed by canonical MCP tool adapters."""

    def __init__(
        self,
        *,
        dialect: str,
        mcp_repository: MCPClientRepository,
    ) -> None:
        self._dialect = dialect
        self._mcp_repository = mcp_repository

    def execute_read_only(
        self,
        database_id: str,
        sql_query: str,
        connection_config: dict,
    ) -> dict:
        row_limit = connection_config.get("row_limit")
        timeout_ms = connection_config.get("timeout_ms")
        parameters = connection_config.get("parameters") or {}

        request = MCPExecuteRequest(
            dialect=self._dialect,
            database_id=database_id,
            sql=sql_query,
            parameters=parameters,
            row_limit=row_limit,
            timeout_ms=int(timeout_ms) if timeout_ms is not None else 30000,
            meta=MCPToolRequestMeta(request_id=f"mcp-exec-{uuid4().hex}"),
        )
        response = self._mcp_repository.execute_read_only(request)
        if response.status == "error":
            raise RuntimeError(f"{response.error.code}: {response.error.message}")

        return {
            "database_id": database_id,
            "columns": response.result.columns,
            "rows": response.result.rows,
            "row_count": response.result.row_count,
            "truncated": response.result.truncated,
            "elapsed_ms": response.result.elapsed_ms,
        }


def _normalize_execution_dialect(dialect: str) -> str:
    normalized = dialect.strip().lower()
    if normalized in _EXECUTION_DIALECT_ALIASES:
        return _EXECUTION_DIALECT_ALIASES[normalized]

    supported = ", ".join(sorted(set(_EXECUTION_DIALECT_ALIASES.values())))
    raise ValueError(f"Unsupported dialect '{dialect}'. Supported dialects: {supported}")


def get_query_execution_repository(
    dialect: str,
    connection_config: dict | None = None,
) -> QueryExecutionRepository:
    """Return a dialect-aware MCP-backed query execution repository."""
    normalized = _normalize_execution_dialect(dialect)
    config = connection_config or {}

    if normalized == "sqlite":
        database_path = config.get("path") or config.get("database_path")
        if not database_path:
            raise ValueError("SQLite connection_config must include 'path'")
        return MCPQueryExecutionRepository(
            dialect="sqlite",
            mcp_repository=SQLiteMCPClientRepository(database_path=str(database_path)),
        )

    if normalized == "postgresql":
        username = config.get("username") or config.get("user")
        if not username:
            raise ValueError("PostgreSQL connection_config must include 'username' or 'user'")
        return MCPQueryExecutionRepository(
            dialect="postgresql",
            mcp_repository=PostgreSQLMCPClientRepository(
                host=str(config.get("host") or "").strip(),
                database=str(config.get("database") or "").strip(),
                username=str(username).strip(),
                password=str(config.get("password") or ""),
                port=int(config.get("port", 5432)),
                extra_params=config.get("extra_params") or {},
            ),
        )

    if normalized == "athena":
        return MCPQueryExecutionRepository(
            dialect="athena",
            mcp_repository=AthenaMCPClientRepository(
                endpoint=str(config.get("endpoint") or "").strip(),
                catalog=str(config.get("catalog") or "").strip(),
                database=str(config.get("database") or "").strip(),
                workgroup=str(config.get("workgroup") or "").strip(),
                timeout_ms=int(config.get("timeout_ms", 120000)),
                invoker=config.get("mcp_invoker"),
            ),
        )

    raise NotImplementedError(
        f"Query execution repository for dialect '{normalized}' is not implemented"
    )
