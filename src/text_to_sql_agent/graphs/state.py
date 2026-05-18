"""LangGraph state definition for schema reading workflow."""

from datetime import datetime
from typing import Annotated, TypedDict

from text_to_sql_agent.models import RawIntrospectionResult
from text_to_sql_agent.models import DatabaseSchema


def add_messages(existing_messages: list[str], new_messages: list[str] | str) -> list[str]:
    """Merge state message lists in a LangGraph-compatible way."""
    if isinstance(new_messages, list):
        return existing_messages + new_messages
    return existing_messages + [new_messages]


class SchemaReadState(TypedDict):
    """Typed state for the schema ingestion LangGraph workflow.
    
    Tracks the lifecycle of a single schema read operation from initiation
    through introspection, normalization, persistence, and vector indexing.
    
    Fields are organized into logical groups:
    - Identity: unique request tracking and context
    - Request params: what the user asked for
    - Runtime context: connection and configuration references
    - Step outputs: results from each graph node (as references, not full payloads)
    - Control flow: workflow state and retry logic
    - Observability: errors, warnings, timestamps
    """

    # -----------------------------------------------------------------------
    # Identity
    # -----------------------------------------------------------------------
    request_id: str
    """Unique identifier for this schema read request."""

    database_id: str
    """Target database identifier."""

    dialect: str | None
    """SQL dialect (sqlite, postgresql, mysql, mssql). None until introspection."""

    # -----------------------------------------------------------------------
    # Request params
    # -----------------------------------------------------------------------
    refresh_mode: str
    """One of: full, incremental, metadata_only."""

    target_tables: list[str] | None
    """Optional list of table names to restrict refresh. None means all tables."""

    force_refresh: bool
    """If True, bypass staleness checks and refresh immediately."""

    # -----------------------------------------------------------------------
    # Runtime context
    # -----------------------------------------------------------------------
    connection_config_ref: str
    """Reference to connection config source (e.g., env var name, config key).
    
    Should NOT contain actual credentials or DSN strings.
    """

    # -----------------------------------------------------------------------
    # Step outputs: references, not full payloads
    # -----------------------------------------------------------------------
    introspection_result: RawIntrospectionResult | None
    """Raw introspection output from the database.
    
    Set by 'introspect_schema' node. May be large, so only store reference key
    in production if needed; here we store the full result for simplicity.
    """

    snapshot_id: str | None
    """Reference ID to the persisted canonical DatabaseSchema snapshot.
    
    Set by 'persist_schema_snapshot' node.
    """

    normalized_schema: DatabaseSchema | None
    """Canonical normalized schema produced by 'normalize_schema' node."""

    document_ids: list[str]
    """List of document IDs created for vector indexing.
    
    Set by 'build_schema_documents' node.
    """

    embedding_ids: list[str]
    """List of embedding record IDs created in vector store.
    
    Set by 'index_schema_embeddings' node.
    """

    # -----------------------------------------------------------------------
    # Control flow
    # -----------------------------------------------------------------------
    status: str
    """Workflow status: pending, introspecting, normalizing, persisting,
    indexing, done, failed.
    """

    current_node: str | None
    """Name of the currently executing or last executed node."""

    retry_count: int
    """Number of retries attempted. Used for retry logic and observability."""

    # -----------------------------------------------------------------------
    # Observability
    # -----------------------------------------------------------------------
    errors: Annotated[list[str], add_messages]
    """Accumulated error messages. Uses add_messages reducer for LangGraph."""

    warnings: Annotated[list[str], add_messages]
    """Accumulated warning messages. Uses add_messages reducer for LangGraph."""

    introspected_at: datetime | None
    """Timestamp when introspection started or completed. None until introspection."""

    completed_at: datetime | None
    """Timestamp when the entire workflow completed (success or failure)."""
