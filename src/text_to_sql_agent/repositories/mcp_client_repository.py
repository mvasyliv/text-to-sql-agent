"""Abstract repository contract for MCP-backed database operations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from text_to_sql_agent.models import (
    MCPExecuteRequest,
    MCPHealthRequest,
    MCPSchemaRequest,
    MCPToolResponse,
)


class MCPClientRepository(ABC):
    """Abstract base class for dialect-specific MCP database clients.

    Concrete implementations adapt one transport/runtime combination for a
    target dialect and expose the canonical MCP tool contract defined in
    `text_to_sql_agent.models.mcp_contract`.
    """

    @abstractmethod
    def execute_tool(
        self,
        request: MCPExecuteRequest | MCPSchemaRequest | MCPHealthRequest,
    ) -> MCPToolResponse:
        """Execute a typed MCP tool request and return the canonical response."""

    @abstractmethod
    def execute_read_only(
        self,
        request: MCPExecuteRequest,
    ) -> MCPToolResponse:
        """Execute the canonical read-only SQL tool for the target dialect."""

    @abstractmethod
    def fetch_schema(
        self,
        request: MCPSchemaRequest,
    ) -> MCPToolResponse:
        """Fetch schema metadata through the canonical MCP schema tool."""

    @abstractmethod
    def check_health(
        self,
        request: MCPHealthRequest,
    ) -> MCPToolResponse:
        """Run the canonical MCP health-check tool for the target dialect."""