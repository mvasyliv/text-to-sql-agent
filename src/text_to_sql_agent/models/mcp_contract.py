"""Typed MCP tool contract models for database execution and schema access."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

MCPToolName = Literal[
    "mcp.db.execute",
    "mcp.db.schema",
    "mcp.db.health",
]

MCPDialect = Literal["sqlite", "postgresql", "athena"]

MCPToolStatus = Literal["success", "error"]

MCPErrorCode = Literal[
    "invalid_request",
    "forbidden_operation",
    "unauthorized",
    "unsupported_dialect",
    "tool_unavailable",
    "timeout",
    "execution_failed",
    "schema_not_found",
    "transport_error",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MCPToolRequestMeta(BaseModel):
    """Shared metadata attached to every MCP tool request."""

    request_id: str = Field(description="Client-provided unique request identifier.")
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation identifier for trace correlation.",
    )
    user_id: str | None = Field(
        default=None,
        description="Optional user identifier for audit correlation.",
    )
    issued_at: datetime = Field(
        default_factory=_utcnow,
        description="UTC timestamp when the request was created.",
    )


class MCPExecuteRequest(BaseModel):
    """Request schema for the canonical SQL execution tool."""

    tool_name: Literal["mcp.db.execute"] = "mcp.db.execute"
    dialect: MCPDialect = Field(description="Target SQL dialect for execution.")
    database_id: str = Field(description="Logical target database identifier.")
    sql: str = Field(description="Read-only SQL statement to execute.")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Named SQL parameters used by the statement.",
    )
    row_limit: int | None = Field(
        default=None,
        ge=1,
        description="Optional upper bound on returned rows.",
    )
    timeout_ms: int = Field(
        default=30000,
        ge=1,
        description="Execution timeout in milliseconds.",
    )
    meta: MCPToolRequestMeta


class MCPSchemaRequest(BaseModel):
    """Request schema for the canonical schema-access tool."""

    tool_name: Literal["mcp.db.schema"] = "mcp.db.schema"
    dialect: MCPDialect = Field(description="Target SQL dialect for introspection.")
    database_id: str = Field(description="Logical target database identifier.")
    schema_names: list[str] | None = Field(
        default=None,
        description="Optional schema namespace filters.",
    )
    table_names: list[str] | None = Field(
        default=None,
        description="Optional table name filters.",
    )
    include_views: bool = Field(
        default=True,
        description="Whether schema response may include views.",
    )
    meta: MCPToolRequestMeta


class MCPHealthRequest(BaseModel):
    """Request schema for the canonical adapter/server health tool."""

    tool_name: Literal["mcp.db.health"] = "mcp.db.health"
    dialect: MCPDialect = Field(description="Target SQL dialect for health probing.")
    database_id: str = Field(description="Logical target database identifier.")
    timeout_ms: int = Field(
        default=3000,
        ge=1,
        description="Health-check timeout in milliseconds.",
    )
    meta: MCPToolRequestMeta


class MCPExecuteSuccessPayload(BaseModel):
    """Successful payload for SQL execution results."""

    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(ge=0)
    truncated: bool = Field(default=False)
    elapsed_ms: int = Field(ge=0)


class MCPSchemaColumn(BaseModel):
    """Column metadata returned by schema-access tool."""

    name: str
    data_type: str
    nullable: bool


class MCPSchemaTable(BaseModel):
    """Table metadata returned by schema-access tool."""

    name: str
    schema_name: str | None = None
    table_type: Literal["TABLE", "VIEW", "MATERIALIZED_VIEW"] = "TABLE"
    columns: list[MCPSchemaColumn] = Field(default_factory=list)


class MCPSchemaSuccessPayload(BaseModel):
    """Successful payload for schema-access responses."""

    tables: list[MCPSchemaTable] = Field(default_factory=list)


class MCPHealthSuccessPayload(BaseModel):
    """Successful payload for health-check responses."""

    reachable: bool
    latency_ms: int = Field(ge=0)
    server_version: str | None = None


class MCPToolError(BaseModel):
    """Canonical error payload for MCP tool failures."""

    code: MCPErrorCode
    message: str
    retriable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class MCPToolSuccessResponse(BaseModel):
    """Success envelope returned by MCP tool adapters."""

    tool_name: MCPToolName
    status: Literal["success"] = "success"
    meta: MCPToolRequestMeta
    result: MCPExecuteSuccessPayload | MCPSchemaSuccessPayload | MCPHealthSuccessPayload


class MCPToolErrorResponse(BaseModel):
    """Error envelope returned by MCP tool adapters."""

    tool_name: MCPToolName
    status: Literal["error"] = "error"
    meta: MCPToolRequestMeta
    error: MCPToolError


MCPToolResponse = MCPToolSuccessResponse | MCPToolErrorResponse
