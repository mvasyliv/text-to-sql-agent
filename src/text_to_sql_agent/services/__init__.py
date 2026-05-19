"""Service layer for schema processing and business logic."""

__version__ = "0.0.1"

from .schema_normalization import build_snapshot_id, normalize_raw_schema
from .schema_document_builder import build_schema_documents
from .schema_indexing import index_schema_embeddings
from .query_result_export import export_query_result

__all__ = [
    "build_snapshot_id",
    "build_schema_documents",
    "index_schema_embeddings",
    "normalize_raw_schema",
    "export_query_result",
]