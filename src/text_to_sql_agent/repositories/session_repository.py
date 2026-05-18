"""In-memory session repository for user identity and conversation history.

Provides a simple, injectable store for User, Conversation, and ChatMessage
records. Designed for easy replacement with a persistent backend (PostgreSQL,
SQLite) in a future iteration without changing consumer interfaces.
"""

from abc import ABC, abstractmethod

from text_to_sql_agent.models.session import ChatMessage, Conversation, User


class SessionRepository(ABC):
    """Abstract contract for session persistence."""

    @abstractmethod
    def save_user(self, user: User) -> None:
        """Persist or update a user record."""

    @abstractmethod
    def get_user(self, user_id: str) -> User | None:
        """Return a user by ID, or None if not found."""

    @abstractmethod
    def save_conversation(self, conversation: Conversation) -> None:
        """Persist or update a conversation record."""

    @abstractmethod
    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Return a conversation by ID, or None if not found."""

    @abstractmethod
    def list_conversations(self, user_id: str) -> list[Conversation]:
        """Return all conversations owned by a user, newest first."""

    @abstractmethod
    def append_message(self, message: ChatMessage) -> None:
        """Append a message to a conversation's history."""

    @abstractmethod
    def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        """Return all messages in a conversation, in insertion order."""


class InMemorySessionRepository(SessionRepository):
    """Volatile in-memory implementation suitable for development and tests.

    All data is lost when the process exits. Swap for a database-backed
    implementation for production use.
    """

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[ChatMessage]] = {}

    def save_user(self, user: User) -> None:
        self._users[user.user_id] = user

    def get_user(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def save_conversation(self, conversation: Conversation) -> None:
        self._conversations[conversation.conversation_id] = conversation
        if conversation.conversation_id not in self._messages:
            self._messages[conversation.conversation_id] = []

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)

    def list_conversations(self, user_id: str) -> list[Conversation]:
        owned = [c for c in self._conversations.values() if c.user_id == user_id]
        return sorted(owned, key=lambda c: c.created_at, reverse=True)

    def append_message(self, message: ChatMessage) -> None:
        if message.conversation_id not in self._messages:
            self._messages[message.conversation_id] = []
        self._messages[message.conversation_id].append(message)

    def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        return list(self._messages.get(conversation_id, []))
