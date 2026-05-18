"""Schema reader agent entrypoint for the schema ingestion graph."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from text_to_sql_agent.graphs.state import SchemaReadState
from text_to_sql_agent.models import SchemaRefreshRequest

RequestIdFactory = Callable[[SchemaRefreshRequest], str]


def build_initial_schema_read_state(
    request: SchemaRefreshRequest,
    *,
    request_id: str,
    connection_config_ref: str,
) -> SchemaReadState:
    """Build the initial LangGraph state for a schema refresh request."""
    return {
        "request_id": request_id,
        "database_id": request.database_id,
        "dialect": None,
        "refresh_mode": request.refresh_mode,
        "target_tables": list(request.target_tables) if request.target_tables is not None else None,
        "force_refresh": request.force,
        "connection_config_ref": connection_config_ref,
        "introspection_result": None,
        "normalized_schema": None,
        "snapshot_id": None,
        "document_ids": [],
        "embedding_ids": [],
        "status": "pending",
        "current_node": None,
        "retry_count": 0,
        "errors": [],
        "warnings": [],
        "introspected_at": None,
        "completed_at": None,
    }


def _default_request_id_factory(request: SchemaRefreshRequest) -> str:
    return f"schema-refresh-{request.database_id}-{uuid4().hex}"


@dataclass(slots=True)
class SchemaReaderAgent:
    """Thin orchestration wrapper around the compiled schema ingestion graph."""

    graph: object
    request_id_factory: RequestIdFactory = _default_request_id_factory

    def run(
        self,
        request: SchemaRefreshRequest,
        *,
        connection_config_ref: str,
        request_id: str | None = None,
    ) -> SchemaReadState:
        """Build the initial state and invoke the schema ingestion graph."""
        resolved_request_id = request_id or self.request_id_factory(request)
        initial_state = build_initial_schema_read_state(
            request,
            request_id=resolved_request_id,
            connection_config_ref=connection_config_ref,
        )
        return self.graph.invoke(initial_state)
