"""Service layer for schema processing and business logic."""

__version__ = "0.0.1"

from .schema_normalization import build_snapshot_id, normalize_raw_schema
from .schema_document_builder import build_schema_documents
from .schema_indexing import index_schema_embeddings
from .query_result_export import export_query_result
from .query_analytics import QueryAnalyticsResult, build_one_shot_chart
from .query_insights import QueryInsightResult, build_query_insight
from .audit_trail import build_audit_trail, make_agent_event
from .auth_service import AuthError, AuthResult, AuthService, hash_password, verify_password
from .conversation_history_service import (
    ConversationAccessError,
    ConversationHistoryRecord,
    ConversationHistoryService,
)

__all__ = [
    "AuthError",
    "AuthResult",
    "AuthService",
    "hash_password",
    "verify_password",
    "ConversationAccessError",
    "ConversationHistoryRecord",
    "ConversationHistoryService",
    "build_snapshot_id",
    "build_schema_documents",
    "index_schema_embeddings",
    "normalize_raw_schema",
    "export_query_result",
    "QueryAnalyticsResult",
    "build_one_shot_chart",
    "QueryInsightResult",
    "build_query_insight",
    "build_audit_trail",
    "make_agent_event",
]