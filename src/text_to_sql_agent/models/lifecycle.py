"""Lifecycle and operational models for schema management."""

from datetime import datetime

from pydantic import BaseModel, Field


class SchemaSnapshotRef(BaseModel):
    """Reference and status metadata for a schema snapshot.
    
    Tracks the lifecycle of a saved schema snapshot, including its creation,
    staleness, and indexing status in the vector store.
    """

    snapshot_id: str
    database_id: str
    dialect: str
    created_at: datetime
    table_count: int
    status: str = Field(
        description="One of: fresh, stale, indexing, indexed, failed. "
        "Tracks snapshot lifecycle from creation through vector indexing.",
    )


class SchemaRefreshRequest(BaseModel):
    """Request to refresh schema from a database.
    
    Specifies the database, refresh scope, and parameters for the schema
    reading workflow.
    """

    database_id: str
    refresh_mode: str = Field(
        default="full",
        description="One of: full (entire schema), incremental (changed tables only), "
        "metadata_only (structure without sampling). Default: full.",
    )
    target_tables: list[str] | None = Field(
        default=None,
        description="If set, restrict refresh to these table names. None means all tables.",
    )
    force: bool = Field(
        default=False,
        description="If True, bypass staleness checks and refresh immediately.",
    )
