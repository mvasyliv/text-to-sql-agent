"""Conversation history service with strict user-ownership checks.

This service provides a small boundary between UI handlers and repositories so
all history access paths consistently enforce that a user can only read their
own conversations.
"""

from __future__ import annotations

from dataclasses import dataclass

from text_to_sql_agent.models.session import ChatMessage, Conversation
from text_to_sql_agent.repositories.session_repository import SessionRepository


class ConversationAccessError(Exception):
    """Raised when a conversation is not accessible to the requesting user."""


@dataclass(frozen=True, slots=True)
class ConversationHistoryRecord:
    """Conversation payload used by UI/history consumers."""

    conversation: Conversation
    messages: list[ChatMessage]


class ConversationHistoryService:
    """Read-oriented history service with ownership checks."""

    def __init__(self, session_repository: SessionRepository) -> None:
        self._repo = session_repository

    def list_user_conversations(self, user_id: str) -> list[Conversation]:
        """Return all conversations owned by the user (newest first)."""
        return self._repo.list_conversations(user_id)

    def load_user_conversation(
        self,
        *,
        user_id: str,
        conversation_id: str,
    ) -> ConversationHistoryRecord:
        """Load one conversation with messages after owner validation.

        Raises:
            ConversationAccessError: if conversation does not exist or does not
                belong to the requesting user.
        """
        conversation = self._repo.get_conversation(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ConversationAccessError("Conversation not found for this user.")

        messages = self._repo.list_messages(conversation_id)
        return ConversationHistoryRecord(conversation=conversation, messages=messages)

