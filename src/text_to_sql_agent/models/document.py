"""Document and embedding models for semantic schema retrieval."""

from datetime import datetime

from pydantic import BaseModel, Field


class SchemaDocument(BaseModel):
    """A semantic document chunk for vector indexing and retrieval.
    
    Represents a single piece of schema metadata that will be embedded
    and stored in the vector store for semantic search.
    """

    doc_id: str
    database_id: str
    snapshot_id: str
    granularity: str = Field(
        description="One of: table, column_group, relationship",
    )
    table_name: str
    column_names: list[str] = Field(default_factory=list)
    content: str = Field(
        description="Human-readable text for embedding. "
        "Example: 'Table orders contains customer purchase records. "
        "Columns: id (PK), customer_id (FK → customers.id), total_amount, status, created_at.'"
    )
    domain_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class SchemaEmbeddingRecord(BaseModel):
    """A vector embedding record for a schema document.
    
    Stores the computed embedding vector and metadata linking it back
    to the original document and database snapshot.
    """

    embedding_id: str
    doc_id: str
    database_id: str
    snapshot_id: str
    vector: list[float] = Field(
        description="Embedding vector (e.g., 1536 dimensions for OpenAI embeddings)."
    )
    indexed_at: datetime
