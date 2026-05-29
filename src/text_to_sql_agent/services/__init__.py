"""Service layer for schema processing and business logic."""

__version__ = "0.0.1"

from .schema_normalization import build_snapshot_id, normalize_raw_schema
from .schema_document_builder import build_schema_documents
from .schema_indexing import index_schema_embeddings
from .query_result_export import export_query_result
from .query_analytics import QueryAnalyticsResult, build_one_shot_chart
from .query_analytics_derivation import (
    ChartDerivationStrategy,
    QueryAnalyticsChartDerivation,
    build_category_sum_derivation,
    build_frequency_derivation,
    build_numeric_line_derivation,
    build_row_count_fallback_derivation,
    derive_one_shot_chart,
    detect_categorical_columns,
    detect_numeric_columns,
    is_number,
)
from .query_insights import QueryInsightResult, build_query_insight
from .query_insights_derivation import (
    QueryInsightDerivation,
    build_no_rows_insight,
    build_query_insight_derivation,
    safe_list_length,
)
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
    "ChartDerivationStrategy",
    "QueryAnalyticsChartDerivation",
    "build_category_sum_derivation",
    "build_frequency_derivation",
    "build_numeric_line_derivation",
    "build_row_count_fallback_derivation",
    "derive_one_shot_chart",
    "detect_categorical_columns",
    "detect_numeric_columns",
    "is_number",
    "QueryInsightResult",
    "build_query_insight",
    "QueryInsightDerivation",
    "build_no_rows_insight",
    "build_query_insight_derivation",
    "safe_list_length",
    "build_audit_trail",
    "make_agent_event",
]