"""Lifecycle and operational models for schema management."""

from datetime import datetime

from pydantic import BaseModel, Field


class SchemaSnapshotRef(BaseModel):
    """Reference and status metadata for a schema snapshot.
    
    Tracks the lifecycle of a saved schema snapshot, including its creation,
    staleness, and indexing status in the vector store.
    """

    snapshot_id: str = Field(
        description="Stable identifier of the stored schema snapshot.",
    )
    database_id: str = Field(
        description="Logical database identifier that this snapshot belongs to.",
    )
    dialect: str = Field(
        description="SQL dialect used when the snapshot was produced.",
    )
    created_at: datetime = Field(
        description="UTC timestamp when the snapshot metadata record was created.",
    )
    table_count: int = Field(
        description="Number of tables captured in the snapshot.",
    )
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
