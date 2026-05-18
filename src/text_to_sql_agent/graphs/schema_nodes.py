"""LangGraph node functions for schema ingestion workflow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

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
    index_schema_embeddings as index_schema_embeddings_service,
    normalize_raw_schema,
)

ConnectionConfig = dict[str, Any]
ConnectionConfigResolver = Callable[[str], ConnectionConfig]
ProviderFactory = Callable[[str], SchemaIntrospectionProvider]
SchemaNormalizer = Callable[[Any], DatabaseSchema]
DocumentBuilder = Callable[[DatabaseSchema], list[SchemaDocument]]


def load_connection_context(
    state: SchemaReadState,
    connection_config_resolver: ConnectionConfigResolver,
) -> dict[str, Any]:
    """Validate that the connection configuration reference can be resolved."""
    connection_config = connection_config_resolver(state["connection_config_ref"])

    dialect = connection_config.get("dialect")
    warnings: list[str] = []
    if not dialect:
        warnings.append("Resolved connection config does not declare a dialect.")

    return {
        "current_node": "load_connection_context",
        "warnings": warnings,
        "dialect": dialect or state.get("dialect"),
    }


def introspect_schema(
    state: SchemaReadState,
    connection_config_resolver: ConnectionConfigResolver,
    provider_factory: ProviderFactory = get_introspection_provider,
) -> dict[str, Any]:
    """Introspect the target database using the resolved provider."""
    connection_config = connection_config_resolver(state["connection_config_ref"])
    dialect = (state.get("dialect") or connection_config.get("dialect") or "").strip().lower()
    if not dialect:
        raise ValueError("Unable to determine dialect for schema introspection")

    provider = provider_factory(dialect)
    result = provider.introspect(state["database_id"], connection_config)

    return {
        "current_node": "introspect_schema",
        "status": "introspecting",
        "dialect": result.dialect,
        "introspection_result": result,
        "introspected_at": result.introspected_at,
    }


def normalize_schema(
    state: SchemaReadState,
    schema_normalizer: SchemaNormalizer = normalize_raw_schema,
) -> dict[str, Any]:
    """Normalize the raw introspection result into the canonical schema model."""
    raw_result = state.get("introspection_result")
    if raw_result is None:
        raise ValueError("introspection_result is required before normalization")

    normalized_schema = schema_normalizer(raw_result)

    return {
        "current_node": "normalize_schema",
        "status": "normalizing",
        "normalized_schema": normalized_schema,
    }


def build_schema_documents(
    state: SchemaReadState,
    document_builder: DocumentBuilder = build_schema_documents_service,
) -> dict[str, Any]:
    """Build semantic schema documents from the normalized schema."""
    normalized_schema = state.get("normalized_schema")
    if normalized_schema is None:
        raise ValueError("normalized_schema is required before building documents")

    documents = document_builder(normalized_schema)
    document_ids = [document.doc_id for document in documents]

    return {
        "current_node": "build_schema_documents",
        "status": "persisting",
        "document_ids": document_ids,
    }


def persist_schema_snapshot(
    state: SchemaReadState,
    snapshot_repository: SchemaSnapshotRepository,
) -> dict[str, Any]:
    """Persist the canonical schema snapshot to disk or another repository."""
    normalized_schema = state.get("normalized_schema")
    if normalized_schema is None:
        raise ValueError("normalized_schema is required before snapshot persistence")

    snapshot_ref = snapshot_repository.save(normalized_schema)

    return {
        "current_node": "persist_schema_snapshot",
        "status": "persisting",
        "snapshot_id": snapshot_ref.snapshot_id,
    }


def index_schema_embeddings(
    state: SchemaReadState,
    vector_store: VectorStoreRepository,
    embedder: Callable[[str], list[float]],
    document_builder: DocumentBuilder = build_schema_documents_service,
    indexed_at: datetime | None = None,
) -> dict[str, Any]:
    """Generate and persist embeddings for the normalized schema documents."""
    normalized_schema = state.get("normalized_schema")
    if normalized_schema is None:
        raise ValueError("normalized_schema is required before embedding indexing")

    documents = document_builder(normalized_schema)
    document_ids = [document.doc_id for document in documents]
    embedding_ids = index_schema_embeddings_service(
        documents,
        vector_store,
        embedder,
        indexed_at=indexed_at or datetime.now(timezone.utc),
    )

    return {
        "current_node": "index_schema_embeddings",
        "status": "indexing",
        "document_ids": document_ids,
        "embedding_ids": embedding_ids,
    }