"""Data models for the text-to-SQL agent."""

__version__ = "0.0.1"

from .document import (
    SchemaDocument,
    SchemaEmbeddingRecord,
)
from .introspection import (
    RawColumnMeta,
    RawForeignKeyMeta,
    RawIndexMeta,
    RawIntrospectionResult,
    RawTableMeta,
)
from .lifecycle import (
    SchemaRefreshRequest,
    SchemaSnapshotRef,
)
from .schema import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeySchema,
    TableSchema,
)

__all__ = [
    "ColumnSchema",
    "DatabaseSchema",
    "ForeignKeySchema",
    "RawColumnMeta",
    "RawForeignKeyMeta",
    "RawIndexMeta",
    "RawIntrospectionResult",
    "RawTableMeta",
    "SchemaDocument",
    "SchemaEmbeddingRecord",
    "SchemaRefreshRequest",
    "SchemaSnapshotRef",
    "TableSchema",
]
