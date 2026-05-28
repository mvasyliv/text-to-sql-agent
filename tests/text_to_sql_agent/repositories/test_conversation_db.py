"""Tests for conversation database bootstrap and connection factory."""
from pathlib import Path
import pytest
import sqlite3
from text_to_sql_agent.repositories.conversation_db import (
    bootstrap_schema,
    get_connection,
    managed_connection,
)
@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "conversation.db"
class TestBootstrapSchema:
    def test_creates_database_file(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        assert db_path.exists()
    def test_creates_users_table(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        with managed_connection(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            assert cursor.fetchone() is not None
    def test_creates_conversations_table(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        with managed_connection(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            assert cursor.fetchone() is not None
    def test_creates_messages_table(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        with managed_connection(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
            assert cursor.fetchone() is not None
    def test_is_idempotent(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        bootstrap_schema(db_path)
        with managed_connection(db_path) as conn:
            cursor = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
            count = cursor.fetchone()[0]
        assert count == 3
    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "data" / "sub" / "conversation.db"
        bootstrap_schema(nested)
        assert nested.exists()
    def test_users_table_has_unique_username_index(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        with managed_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_users_username'"
            )
            assert cursor.fetchone() is not None
    def test_username_uniqueness_enforced(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        with managed_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO users (user_id, username, password_hash, display_name, created_at, updated_at) "
                "VALUES ('u1', 'alice', 'hash', 'Alice', '2026-01-01', '2026-01-01')"
            )
            conn.commit()
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO users (user_id, username, password_hash, display_name, created_at, updated_at) "
                    "VALUES ('u2', 'alice', 'hash2', 'Alice2', '2026-01-01', '2026-01-01')"
                )
    def test_foreign_key_on_conversations_enforced(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        with managed_connection(db_path) as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO conversations (conversation_id, user_id, created_at, updated_at) "
                    "VALUES ('c1', 'nonexistent-user', '2026-01-01', '2026-01-01')"
                )
                conn.commit()
class TestGetConnection:
    def test_returns_connection(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        conn = get_connection(db_path)
        assert conn is not None
        conn.close()
    def test_row_factory_is_set(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        with managed_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO users (user_id, username, password_hash, display_name, created_at, updated_at) "
                "VALUES ('u1', 'alice', 'hash', 'Alice', '2026-01-01', '2026-01-01')"
            )
            conn.commit()
            cursor = conn.execute("SELECT * FROM users WHERE username='alice'")
            row = cursor.fetchone()
            assert row["username"] == "alice"
class TestManagedConnection:
    def test_closes_connection_on_exit(self, db_path: Path) -> None:
        bootstrap_schema(db_path)
        with managed_connection(db_path) as conn:
            assert conn is not None
        with pytest.raises(Exception):
            conn.execute("SELECT 1")
