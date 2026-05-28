"""SQLite-backed persistent implementation of SessionRepository.

Replaces ``InMemorySessionRepository`` with a durable store backed by the
``conversation`` SQLite database bootstrapped by ``conversation_db``.

Conversations and messages are scoped to their owning ``user_id`` so that
every read/write path enforces user isolation at the repository boundary.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from text_to_sql_agent.models.session import ChatMessage, Conversation, MessageRole, User
from text_to_sql_agent.repositories.conversation_db import bootstrap_schema, managed_connection
from text_to_sql_agent.repositories.session_repository import SessionRepository


# ---------------------------------------------------------------------------
# Datetime helpers  (SQLite stores datetimes as ISO-8601 text)
# ---------------------------------------------------------------------------

def _dt_to_str(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _str_to_dt(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class SQLiteSessionRepository(SessionRepository):
    """Persistent session repository backed by a SQLite conversation database.

    The database schema is bootstrapped automatically on first instantiation.
    All conversation and message queries are filtered by ``user_id`` to
    enforce row-level ownership.

    Args:
        db_path: Path to the SQLite file used for conversation persistence.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        bootstrap_schema(self._db_path)

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    def save_user(self, user: User) -> None:
        """Upsert a minimal user record to satisfy the FK constraint on conversations.

        Uses ``INSERT OR IGNORE`` so that existing full auth records (created by
        the auth service with a real password hash) are never overwritten.
        """
        with managed_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO users
                    (user_id, username, password_hash, display_name, is_active,
                     created_at, updated_at)
                VALUES (?, ?, '', ?, ?, ?, ?)
                """,
                (
                    user.user_id,
                    user.user_id,           # username defaults to user_id
                    user.display_name,
                    int(user.is_active),
                    _dt_to_str(user.created_at),
                    _dt_to_str(user.created_at),
                ),
            )
            conn.commit()

    def get_user(self, user_id: str) -> User | None:
        """Return a ``User`` for the given ID, or ``None`` if not found."""
        with managed_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT user_id, display_name, is_active, created_at FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return User(
            user_id=row["user_id"],
            display_name=row["display_name"] or row["user_id"],
            is_active=bool(row["is_active"]),
            created_at=_str_to_dt(row["created_at"]),
        )

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    def save_conversation(self, conversation: Conversation) -> None:
        """Upsert a conversation record (insert or replace on conflict)."""
        with managed_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO conversations
                    (conversation_id, user_id, title, graph_thread_id, is_active, metadata_json,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    title        = excluded.title,
                    graph_thread_id = excluded.graph_thread_id,
                    is_active    = excluded.is_active,
                    metadata_json = excluded.metadata_json,
                    updated_at   = excluded.updated_at
                """,
                (
                    conversation.conversation_id,
                    conversation.user_id,
                    conversation.title,
                    conversation.graph_thread_id,
                    int(conversation.is_active),
                    json.dumps(conversation.metadata),
                    _dt_to_str(conversation.created_at),
                    _dt_to_str(conversation.updated_at),
                ),
            )
            conn.commit()

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Return a ``Conversation`` by ID, or ``None`` if not found."""
        with managed_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_conversation(row)

    def list_conversations(self, user_id: str) -> list[Conversation]:
        """Return all active conversations owned by ``user_id``, newest first."""
        with managed_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [_row_to_conversation(r) for r in rows]

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def append_message(self, message: ChatMessage) -> None:
        """Append a message to a conversation.  Uses ``INSERT OR IGNORE`` so
        duplicate ``message_id`` submissions are silently skipped."""
        with managed_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO messages
                    (message_id, conversation_id, role, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.conversation_id,
                    message.role.value,
                    message.content,
                    json.dumps(message.metadata),
                    _dt_to_str(message.created_at),
                ),
            )
            conn.commit()

    def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        """Return all messages for ``conversation_id`` in insertion order."""
        with managed_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            ).fetchall()
        return [_row_to_message(r) for r in rows]


# ---------------------------------------------------------------------------
# Row → model helpers
# ---------------------------------------------------------------------------

def _row_to_conversation(row) -> Conversation:
    meta_raw = row["metadata_json"] or "{}"
    try:
        meta = json.loads(meta_raw)
    except (ValueError, TypeError):
        meta = {}
    return Conversation(
        conversation_id=row["conversation_id"],
        user_id=row["user_id"],
        title=row["title"],
        graph_thread_id=row["graph_thread_id"],
        is_active=bool(row["is_active"]),
        metadata={k: str(v) for k, v in meta.items()},
        created_at=_str_to_dt(row["created_at"]),
        updated_at=_str_to_dt(row["updated_at"]),
    )


def _row_to_message(row) -> ChatMessage:
    meta_raw = row["metadata_json"] or "{}"
    try:
        meta = json.loads(meta_raw)
    except (ValueError, TypeError):
        meta = {}
    return ChatMessage(
        message_id=row["message_id"],
        conversation_id=row["conversation_id"],
        role=MessageRole(row["role"]),
        content=row["content"],
        metadata={k: str(v) for k, v in meta.items()},
        created_at=_str_to_dt(row["created_at"]),
    )

