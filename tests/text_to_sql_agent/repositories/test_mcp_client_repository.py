"""Tests for abstract MCP client repository contract."""

from typing import Any

import pytest

from text_to_sql_agent.models import (
    MCPExecuteRequest,
    MCPExecuteSuccessPayload,
    MCPHealthRequest,
    MCPHealthSuccessPayload,
    MCPSchemaRequest,
    MCPSchemaSuccessPayload,
    MCPToolRequestMeta,
    MCPToolSuccessResponse,
)
from text_to_sql_agent.repositories import MCPClientRepository


def _meta() -> MCPToolRequestMeta:
    return MCPToolRequestMeta(request_id="req-001", user_id="u-001", conversation_id="c-001")


class MockMCPClientRepository(MCPClientRepository):
    """Concrete mock implementation for abstract contract tests."""

    def execute_tool(
        self,
        request: MCPExecuteRequest | MCPSchemaRequest | MCPHealthRequest,
    ) -> MCPToolSuccessResponse:
        if isinstance(request, MCPExecuteRequest):
            return self.execute_read_only(request)
        if isinstance(request, MCPSchemaRequest):
            return self.fetch_schema(request)
        return self.check_health(request)

    def execute_read_only(self, request: MCPExecuteRequest) -> MCPToolSuccessResponse:
        return MCPToolSuccessResponse(
            tool_name=request.tool_name,
            meta=request.meta,
            result=MCPExecuteSuccessPayload(
                columns=["value"],
                rows=[{"value": 1}],
                row_count=1,
                truncated=False,
                elapsed_ms=5,
            ),
        )

    def fetch_schema(self, request: MCPSchemaRequest) -> MCPToolSuccessResponse:
        return MCPToolSuccessResponse(
            tool_name=request.tool_name,
            meta=request.meta,
            result=MCPSchemaSuccessPayload(tables=[]),
        )

    def check_health(self, request: MCPHealthRequest) -> MCPToolSuccessResponse:
        return MCPToolSuccessResponse(
            tool_name=request.tool_name,
            meta=request.meta,
            result=MCPHealthSuccessPayload(reachable=True, latency_ms=3, server_version="test"),
        )


def test_mcp_client_repository_cannot_instantiate_directly() -> None:
    with pytest.raises(TypeError) as exc_info:
        MCPClientRepository()  # type: ignore[abstract]
    assert "abstract" in str(exc_info.value).lower()


def test_mcp_client_repository_requires_method_implementation() -> None:
    class IncompleteMCPClientRepository(MCPClientRepository):
        pass

    with pytest.raises(TypeError):
        IncompleteMCPClientRepository()  # type: ignore[abstract]


def test_mock_mcp_client_repository_execute_read_only() -> None:
    repository = MockMCPClientRepository()
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="sqlite",
            database_id="db-main",
            sql="SELECT 1",
            meta=_meta(),
        )
    )

    assert response.tool_name == "mcp.db.execute"
    assert response.result.row_count == 1


def test_mock_mcp_client_repository_fetch_schema() -> None:
    repository = MockMCPClientRepository()
    response = repository.fetch_schema(
        MCPSchemaRequest(
            dialect="postgresql",
            database_id="analytics",
            meta=_meta(),
        )
    )

    assert response.tool_name == "mcp.db.schema"
    assert response.result.tables == []


def test_mock_mcp_client_repository_check_health() -> None:
    repository = MockMCPClientRepository()
    response = repository.check_health(
        MCPHealthRequest(
            dialect="athena",
            database_id="warehouse",
            meta=_meta(),
        )
    )

    assert response.tool_name == "mcp.db.health"
    assert response.result.reachable is True


def test_execute_tool_dispatches_by_request_type() -> None:
    repository = MockMCPClientRepository()

    execute_response = repository.execute_tool(
        MCPExecuteRequest(
            dialect="sqlite",
            database_id="db-main",
            sql="SELECT 1",
            meta=_meta(),
        )
    )
    schema_response = repository.execute_tool(
        MCPSchemaRequest(
            dialect="postgresql",
            database_id="db-main",
            meta=_meta(),
        )
    )
    health_response = repository.execute_tool(
        MCPHealthRequest(
            dialect="athena",
            database_id="db-main",
            meta=_meta(),
        )
    )

    assert execute_response.tool_name == "mcp.db.execute"
    assert schema_response.tool_name == "mcp.db.schema"
    assert health_response.tool_name == "mcp.db.health"