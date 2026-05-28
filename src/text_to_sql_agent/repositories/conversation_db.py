"""Conversation database bootstrap and connection factory.

Manages the SQLite database used for user accounts, conversations, and
chat message persistence.  Provides:

- ``get_connection()`` — returns an open ``sqlite3.Connection`` to the DB.
- ``bootstrap_schema()`` — creates all required tables and indexes if they
  do not yet exist (idempotent, safe to call on every startup).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# DDL executed once per database file to establish the schema.
# All statements use IF NOT EXISTS so repeated calls are safe.
_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id      TEXT PRIMARY KEY,
    username     TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
    ON users (username);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id  TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title            TEXT,
    graph_thread_id  TEXT,
    is_active        INTEGER NOT NULL DEFAULT 1,
    metadata_json    TEXT NOT NULL DEFAULT '{}',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
    ON conversations (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    message_id      TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL DEFAULT '',
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON messages (conversation_id, created_at ASC);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open and return a ``sqlite3.Connection`` to the conversation database.

    Foreign-key enforcement is enabled on every connection.  The caller is
    responsible for closing the connection when done.
    """
    connection = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def managed_connection(db_path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    """Context manager that opens, yields, and closes a database connection."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def bootstrap_schema(db_path: str | Path) -> None:
    """Create all tables and indexes in the conversation database.

    Idempotent — safe to call on every application startup.  Existing data is
    never modified or dropped.

    Args:
        db_path: Path to the SQLite file.  The file and any parent directories
                 are created if they do not yet exist.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with managed_connection(path) as conn:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()

