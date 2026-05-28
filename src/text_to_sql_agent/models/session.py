"""User identity, conversation, and chat message models."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MessageRole(str, Enum):
    """Role of a participant in a conversation turn."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class User(BaseModel):
    """Represents an authenticated user of the system.

    Each user has a stable identifier used to isolate sessions and track history.
    """

    user_id: str = Field(description="Stable unique identifier for the user.")
    display_name: str = Field(description="Human-readable name shown in the UI.")
    email: str | None = Field(
        default=None,
        description="Optional email address, used for auth provider linkage.",
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp when the user record was first created.",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active.",
    )


class Conversation(BaseModel):
    """A single conversation session between a user and the DB assistant.

    Scopes all messages, approval events, and query executions to one
    user-initiated interaction thread.
    """

    conversation_id: str = Field(description="Unique identifier for this conversation.")
    user_id: str = Field(description="Owner of this conversation.")
    title: str | None = Field(
        default=None,
        description="Optional short title derived from the first user message.",
    )
    graph_thread_id: str | None = Field(
        default=None,
        description="Optional persisted LangGraph thread id for resume continuity.",
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp when the conversation was started.",
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp of the last activity in this conversation.",
    )
    is_active: bool = Field(
        default=True,
        description="False when the conversation is closed or archived.",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Optional free-form key-value pairs (e.g. db_id, dialect).",
    )


class ChatMessage(BaseModel):
    """A single message turn within a conversation.

    Covers user questions, assistant responses, tool invocations, and
    system events such as SQL approval or rejection.
    """

    message_id: str = Field(description="Unique identifier for this message.")
    conversation_id: str = Field(description="Conversation this message belongs to.")
    role: MessageRole = Field(description="Who produced this message.")
    content: str = Field(description="Text content of the message.")
    created_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp when the message was recorded.",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Optional structured data attached to the message. "
            "For tool messages: sql, approval_status, row_count, etc."
        ),
    )
