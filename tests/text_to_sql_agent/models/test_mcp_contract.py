"""Tests for MCP tool contract models."""

from datetime import timezone

import pytest
from pydantic import ValidationError

from text_to_sql_agent.models.mcp_contract import (
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
    MCPToolSuccessResponse,
)


def _meta() -> MCPToolRequestMeta:
    return MCPToolRequestMeta(request_id="req-001", conversation_id="c-001", user_id="u-001")


def test_execute_request_defaults_and_roundtrip() -> None:
    request = MCPExecuteRequest(
        dialect="sqlite",
        database_id="db-main",
        sql="SELECT 1",
        meta=_meta(),
    )
    assert request.tool_name == "mcp.db.execute"
    assert request.timeout_ms == 30000
    assert request.parameters == {}
    assert request.meta.issued_at.tzinfo == timezone.utc

    restored = MCPExecuteRequest.model_validate(request.model_dump())
    assert restored == request


def test_execute_request_rejects_invalid_limit() -> None:
    with pytest.raises(ValidationError):
        MCPExecuteRequest(
            dialect="postgresql",
            database_id="db-main",
            sql="SELECT 1",
            row_limit=0,
            meta=_meta(),
        )


def test_schema_request_defaults() -> None:
    request = MCPSchemaRequest(
        dialect="athena",
        database_id="analytics",
        meta=_meta(),
    )
    assert request.tool_name == "mcp.db.schema"
    assert request.include_views is True


def test_health_request_defaults() -> None:
    request = MCPHealthRequest(
        dialect="sqlite",
        database_id="db-main",
        meta=_meta(),
    )
    assert request.tool_name == "mcp.db.health"
    assert request.timeout_ms == 3000


def test_success_response_for_execute_payload() -> None:
    payload = MCPExecuteSuccessPayload(
        columns=["id"],
        rows=[{"id": 1}],
        row_count=1,
        truncated=False,
        elapsed_ms=12,
    )
    response = MCPToolSuccessResponse(
        tool_name="mcp.db.execute",
        meta=_meta(),
        result=payload,
    )
    assert response.status == "success"
    assert response.result.row_count == 1


def test_success_response_for_schema_payload() -> None:
    table = MCPSchemaTable(
        name="users",
        schema_name="public",
        columns=[MCPSchemaColumn(name="id", data_type="INTEGER", nullable=False)],
    )
    payload = MCPSchemaSuccessPayload(tables=[table])
    response = MCPToolSuccessResponse(
        tool_name="mcp.db.schema",
        meta=_meta(),
        result=payload,
    )
    assert response.result.tables[0].name == "users"


def test_error_response_with_taxonomy_code() -> None:
    response = MCPToolErrorResponse(
        tool_name="mcp.db.execute",
        meta=_meta(),
        error=MCPToolError(
            code="forbidden_operation",
            message="Only read-only SQL is allowed.",
            retriable=False,
            details={"operation": "DROP"},
        ),
    )
    assert response.status == "error"
    assert response.error.code == "forbidden_operation"


def test_health_success_payload() -> None:
    payload = MCPHealthSuccessPayload(reachable=True, latency_ms=5, server_version="1.2.3")
    response = MCPToolSuccessResponse(
        tool_name="mcp.db.health",
        meta=_meta(),
        result=payload,
    )
    assert response.result.reachable is True
    assert response.result.latency_ms == 5
