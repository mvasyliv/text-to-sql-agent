"""Repository layer for data access and vendor-specific adapters."""

__version__ = "0.0.1"

from .introspection_provider import SchemaIntrospectionProvider
from .provider_factory import PROVIDER_REGISTRY, get_introspection_provider, normalize_dialect
from .schema_snapshot_repository import SchemaSnapshotRepository
from .vector_store_repository import VectorStoreRepository
from .sqlite_provider import SQLiteIntrospectionProvider
from .postgresql_provider import PostgresIntrospectionProvider
from .session_repository import InMemorySessionRepository, SessionRepository
from .query_execution_repository import QueryExecutionRepository
from .sqlite_query_execution_repository import SQLiteQueryExecutionRepository
from .query_execution_factory import get_query_execution_repository

__all__ = [
    "SchemaIntrospectionProvider",
    "PROVIDER_REGISTRY",
    "get_introspection_provider",
    "normalize_dialect",
    "SchemaSnapshotRepository",
    "VectorStoreRepository",
    "SQLiteIntrospectionProvider",
    "PostgresIntrospectionProvider",
    "InMemorySessionRepository",
    "SessionRepository",
    "QueryExecutionRepository",
    "SQLiteQueryExecutionRepository",
    "get_query_execution_repository",
]
