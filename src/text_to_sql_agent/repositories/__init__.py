"""Repository layer for data access and vendor-specific adapters."""

__version__ = "0.0.1"

from .introspection_provider import SchemaIntrospectionProvider
from .provider_factory import PROVIDER_REGISTRY, get_introspection_provider, normalize_dialect
from .schema_snapshot_repository import SchemaSnapshotRepository
from .vector_store_repository import VectorStoreRepository
from .sqlite_provider import SQLiteIntrospectionProvider
from .postgresql_provider import PostgresIntrospectionProvider
from .session_repository import InMemorySessionRepository, SessionRepository
from .sqlite_auth_repository import SQLiteAuthRepository
from .sqlite_session_repository import SQLiteSessionRepository
from .query_execution_repository import QueryExecutionRepository
from .mcp_client_repository import MCPClientRepository
from .sqlite_mcp_client_repository import SQLiteMCPClientRepository
from .postgresql_mcp_client_repository import PostgreSQLMCPClientRepository
from .athena_mcp_client_repository import AthenaMCPClientRepository
from .sqlite_query_execution_repository import SQLiteQueryExecutionRepository
from .query_execution_factory import get_query_execution_repository

__all__ = [
    "bootstrap_schema",
    "get_connection",
    "managed_connection",
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
    "SQLiteAuthRepository",
    "SQLiteSessionRepository",
    "QueryExecutionRepository",
    "MCPClientRepository",
    "SQLiteMCPClientRepository",
    "PostgreSQLMCPClientRepository",
    "AthenaMCPClientRepository",
    "SQLiteQueryExecutionRepository",
    "get_query_execution_repository",
]
