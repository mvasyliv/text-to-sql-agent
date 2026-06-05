"""Data models for the text-to-SQL agent."""

__version__ = "0.0.1"

from .auth import (
    AuthPrincipal,
    UserAccount,
    UserLogin,
    UserRegistration,
)
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
from .mcp_contract import (
    MCPDialect,
    MCPErrorCode,
    MCPExecuteRequest,
    MCPExecuteSuccessPayload,
    MCPHealthRequest,
    MCPHealthSuccessPayload,
    MCPSchemaColumn,
    MCPSchemaRequest,
    MCPSchemaSuccessPayload,
    MCPSchemaTable,
    MCPToolError,
    MCPToolErrorResponse,
    MCPToolName,
    MCPToolRequestMeta,
    MCPToolResponse,
    MCPToolStatus,
    MCPToolSuccessResponse,
)
from .schema import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeySchema,
    TableSchema,
)
from .session import (
    ChatMessage,
    Conversation,
    MessageRole,
    User,
)
from .trace import (
    AgentEvent,
    AgentEventStatus,
    AgentEventType,
    AuditTrail,
)

__all__ = [
    "AuthPrincipal",
    "UserAccount",
    "UserLogin",
    "UserRegistration",
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
    "MCPDialect",
    "MCPErrorCode",
    "MCPExecuteRequest",
    "MCPExecuteSuccessPayload",
    "MCPHealthRequest",
    "MCPHealthSuccessPayload",
    "MCPSchemaColumn",
    "MCPSchemaRequest",
    "MCPSchemaSuccessPayload",
    "MCPSchemaTable",
    "MCPToolError",
    "MCPToolErrorResponse",
    "MCPToolName",
    "MCPToolRequestMeta",
    "MCPToolResponse",
    "MCPToolStatus",
    "MCPToolSuccessResponse",
    "TableSchema",
    "ChatMessage",
    "Conversation",
    "MessageRole",
    "User",
    "AgentEvent",
    "AgentEventStatus",
    "AgentEventType",
    "AuditTrail",
]
