"""Compiled LangGraph workflow for schema ingestion."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from text_to_sql_agent.graphs.schema_nodes import (
    build_schema_documents as build_schema_documents_node,
    index_schema_embeddings as index_schema_embeddings_node,
    introspect_schema as introspect_schema_node,
    load_connection_context as load_connection_context_node,
    normalize_schema as normalize_schema_node,
    persist_schema_snapshot as persist_schema_snapshot_node,
)
from text_to_sql_agent.graphs.state import SchemaReadState
from text_to_sql_agent.models import DatabaseSchema, SchemaDocument
from text_to_sql_agent.repositories import (
    SchemaIntrospectionProvider,
    SchemaSnapshotRepository,
    VectorStoreRepository,
    get_introspection_provider,
)
from text_to_sql_agent.services import (
    build_schema_documents as build_schema_documents_service,
    normalize_raw_schema,
)

ConnectionConfig = dict[str, Any]
ConnectionConfigResolver = Callable[[str], ConnectionConfig]
ProviderFactory = Callable[[str], SchemaIntrospectionProvider]
SchemaNormalizer = Callable[[Any], DatabaseSchema]
DocumentBuilder = Callable[[DatabaseSchema], list[SchemaDocument]]

_RETRY_LABEL = "retry"
_FAILED_LABEL = "failed"


def _capture_step_failure(state: SchemaReadState, node_name: str, exc: Exception) -> dict[str, Any]:
    retry_count = int(state.get("retry_count", 0)) + 1
    return {
        "current_node": node_name,
        "status": "failed",
        "retry_count": retry_count,
        "errors": [f"{node_name} failed: {exc}"],
    }


def _wrap_step(step_name: str, step_fn: Callable[[SchemaReadState], dict[str, Any]]) -> Callable[[SchemaReadState], dict[str, Any]]:
    def _node(state: SchemaReadState) -> dict[str, Any]:
        try:
            return step_fn(state)
        except Exception as exc:  # pragma: no cover - exercised via graph failure paths
            return _capture_step_failure(state, step_name, exc)

    return _node


def _route_after_step(state: SchemaReadState, success_label: str, *, max_retries: int) -> str:
    if state.get("status") == "failed":
        if int(state.get("retry_count", 0)) <= max_retries:
            return _RETRY_LABEL
        return _FAILED_LABEL

    return success_label


def _build_terminal_state(node_name: str, status: str) -> dict[str, Any]:
    return {
        "current_node": node_name,
        "status": status,
        "completed_at": datetime.now(timezone.utc),
    }


def build_schema_ingestion_graph(
    connection_config_resolver: ConnectionConfigResolver,
    snapshot_repository: SchemaSnapshotRepository,
    vector_store: VectorStoreRepository,
    embedder: Callable[[str], list[float]],
    *,
    provider_factory: ProviderFactory = get_introspection_provider,
    schema_normalizer: SchemaNormalizer = normalize_raw_schema,
    document_builder: DocumentBuilder = build_schema_documents_service,
    indexed_at: datetime | None = None,
    max_retries: int = 1,
):
    """Build the compiled schema ingestion workflow graph."""
    workflow = StateGraph(SchemaReadState)

    workflow.add_node(
        "load_connection_context",
        _wrap_step(
            "load_connection_context",
            lambda state: load_connection_context_node(state, connection_config_resolver),
        ),
    )
    workflow.add_node(
        "introspect_schema",
        _wrap_step(
            "introspect_schema",
            lambda state: introspect_schema_node(state, connection_config_resolver, provider_factory),
        ),
    )
    workflow.add_node(
        "normalize_schema",
        _wrap_step("normalize_schema", lambda state: normalize_schema_node(state, schema_normalizer)),
    )
    workflow.add_node(
        "build_schema_documents",
        _wrap_step("build_schema_documents", lambda state: build_schema_documents_node(state, document_builder)),
    )
    workflow.add_node(
        "persist_schema_snapshot",
        _wrap_step("persist_schema_snapshot", lambda state: persist_schema_snapshot_node(state, snapshot_repository)),
    )
    workflow.add_node(
        "index_schema_embeddings",
        _wrap_step(
            "index_schema_embeddings",
            lambda state: index_schema_embeddings_node(
                state,
                vector_store,
                embedder,
                document_builder=document_builder,
                indexed_at=indexed_at,
            ),
        ),
    )
    workflow.add_node(
        "mark_schema_ingestion_failed",
        lambda state: _build_terminal_state("mark_schema_ingestion_failed", "failed"),
    )
    workflow.add_node(
        "complete_schema_ingestion",
        lambda state: _build_terminal_state("complete_schema_ingestion", "done"),
    )

    workflow.set_entry_point("load_connection_context")

    workflow.add_conditional_edges(
        "load_connection_context",
        lambda state: _route_after_step(state, "introspect_schema", max_retries=max_retries),
        {
            _RETRY_LABEL: "introspect_schema",
            "introspect_schema": "introspect_schema",
            _FAILED_LABEL: "mark_schema_ingestion_failed",
        },
    )
    workflow.add_conditional_edges(
        "introspect_schema",
        lambda state: _route_after_step(state, "normalize_schema", max_retries=max_retries),
        {
            _RETRY_LABEL: "introspect_schema",
            "normalize_schema": "normalize_schema",
            _FAILED_LABEL: "mark_schema_ingestion_failed",
        },
    )
    workflow.add_conditional_edges(
        "normalize_schema",
        lambda state: _route_after_step(state, "build_schema_documents", max_retries=max_retries),
        {
            _RETRY_LABEL: "introspect_schema",
            "build_schema_documents": "build_schema_documents",
            _FAILED_LABEL: "mark_schema_ingestion_failed",
        },
    )
    workflow.add_conditional_edges(
        "build_schema_documents",
        lambda state: _route_after_step(state, "persist_schema_snapshot", max_retries=max_retries),
        {
            _RETRY_LABEL: "introspect_schema",
            "persist_schema_snapshot": "persist_schema_snapshot",
            _FAILED_LABEL: "mark_schema_ingestion_failed",
        },
    )
    workflow.add_conditional_edges(
        "persist_schema_snapshot",
        lambda state: _route_after_step(state, "index_schema_embeddings", max_retries=max_retries),
        {
            _RETRY_LABEL: "introspect_schema",
            "index_schema_embeddings": "index_schema_embeddings",
            _FAILED_LABEL: "mark_schema_ingestion_failed",
        },
    )
    workflow.add_conditional_edges(
        "index_schema_embeddings",
        lambda state: _route_after_step(state, "complete_schema_ingestion", max_retries=max_retries),
        {
            _RETRY_LABEL: "introspect_schema",
            "complete_schema_ingestion": "complete_schema_ingestion",
            _FAILED_LABEL: "mark_schema_ingestion_failed",
        },
    )

    workflow.add_edge("complete_schema_ingestion", END)
    workflow.add_edge("mark_schema_ingestion_failed", END)

    return workflow.compile()
