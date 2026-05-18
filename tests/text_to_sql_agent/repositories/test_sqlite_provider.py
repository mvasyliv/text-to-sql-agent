"""Tests for SQLite schema introspection provider (T-2026-05-15-025)."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from text_to_sql_agent.repositories import SQLiteIntrospectionProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_sqlite_db() -> Path:
    """Create a temporary SQLite database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    # Create test schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create orders table with FK
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            total_amount REAL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Create index
    cursor.execute("CREATE INDEX idx_orders_status ON orders(status)")
    cursor.execute("CREATE UNIQUE INDEX idx_users_email ON users(email)")
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    db_path.unlink()


@pytest.fixture
def provider() -> SQLiteIntrospectionProvider:
    """Create a SQLite introspection provider instance."""
    return SQLiteIntrospectionProvider()


# ---------------------------------------------------------------------------
# Basic Introspection Tests
# ---------------------------------------------------------------------------


def test_sqlite_provider_introspect_basic(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Test basic introspection of a simple SQLite database."""
    result = provider.introspect(
        database_id="test_db",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    assert result.database_id == "test_db"
    assert result.dialect == "sqlite"
    assert len(result.tables) == 2
    assert result.warnings == []


def test_sqlite_provider_tables_discovered(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Verify that both tables are discovered."""
    result = provider.introspect(
        database_id="test_db",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    table_names = [t.name for t in result.tables]
    assert "users" in table_names
    assert "orders" in table_names


def test_sqlite_provider_users_table_columns(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Verify columns in users table."""
    result = provider.introspect(
        database_id="test_db",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    users_table = next((t for t in result.tables if t.name == "users"), None)
    assert users_table is not None
    assert len(users_table.columns) == 4
    
    col_names = [c.name for c in users_table.columns]
    assert "id" in col_names
    assert "username" in col_names
    assert "email" in col_names
    assert "created_at" in col_names


def test_sqlite_provider_column_nullability(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Verify nullability is correctly detected."""
    result = provider.introspect(
        database_id="test_db",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    users_table = next((t for t in result.tables if t.name == "users"), None)
    assert users_table is not None
    
    id_col = next((c for c in users_table.columns if c.name == "id"), None)
    assert id_col is not None
    assert id_col.is_nullable is False
    
    email_col = next((c for c in users_table.columns if c.name == "email"), None)
    assert email_col is not None
    assert email_col.is_nullable is False


def test_sqlite_provider_primary_keys(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Verify primary keys are detected."""
    result = provider.introspect(
        database_id="test_db",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    users_table = next((t for t in result.tables if t.name == "users"), None)
    assert users_table is not None
    
    id_col = next((c for c in users_table.columns if c.name == "id"), None)
    assert id_col is not None
    assert id_col.is_primary_key is True


def test_sqlite_provider_foreign_keys(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Verify foreign keys are detected."""
    result = provider.introspect(
        database_id="test_db",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    orders_table = next((t for t in result.tables if t.name == "orders"), None)
    assert orders_table is not None
    assert len(orders_table.foreign_keys) == 1
    
    fk = orders_table.foreign_keys[0]
    assert fk.from_table == "orders"
    assert fk.from_column == "user_id"
    assert fk.to_table == "users"
    assert fk.to_column == "id"
    assert fk.on_delete == "CASCADE"


def test_sqlite_provider_indexes(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Verify indexes are discovered."""
    result = provider.introspect(
        database_id="test_db",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    orders_table = next((t for t in result.tables if t.name == "orders"), None)
    assert orders_table is not None
    # sqlite_autoindex + idx_orders_status = 2 (at least)
    assert len(orders_table.indexes) >= 1


def test_sqlite_provider_default_values(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Verify default values are captured."""
    result = provider.introspect(
        database_id="test_db",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    orders_table = next((t for t in result.tables if t.name == "orders"), None)
    assert orders_table is not None
    
    status_col = next((c for c in orders_table.columns if c.name == "status"), None)
    assert status_col is not None
    assert "pending" in str(status_col.default_value).lower()


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


def test_sqlite_provider_missing_path_raises() -> None:
    """Verify error when 'path' is missing from config."""
    provider = SQLiteIntrospectionProvider()
    
    with pytest.raises(ValueError) as exc_info:
        provider.introspect(
            database_id="test_db",
            connection_config={},
        )
    assert "path" in str(exc_info.value).lower()


def test_sqlite_provider_invalid_path_raises() -> None:
    """Verify error when database file doesn't exist."""
    provider = SQLiteIntrospectionProvider()
    
    with pytest.raises(sqlite3.Error):
        provider.introspect(
            database_id="test_db",
            connection_config={"path": "/nonexistent/path/to/db.sqlite3"},
        )


def test_sqlite_provider_in_memory_db() -> None:
    """Verify provider works with in-memory database."""
    provider = SQLiteIntrospectionProvider()
    
    # Create in-memory DB and add a table
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()
    
    # SQLite in-memory databases are connection-specific, so this will be empty
    # But we can test that it accepts ":memory:" as a path without error
    result = provider.introspect(
        database_id="memory_db",
        connection_config={"path": ":memory:"},
    )
    assert result.database_id == "memory_db"


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


def test_sqlite_provider_multiple_databases(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Verify provider can handle multiple database introspections."""
    result1 = provider.introspect(
        database_id="db_1",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    result2 = provider.introspect(
        database_id="db_2",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    assert result1.database_id == "db_1"
    assert result2.database_id == "db_2"
    assert len(result1.tables) == len(result2.tables)


def test_sqlite_provider_timestamp_recorded(provider: SQLiteIntrospectionProvider, temp_sqlite_db: Path) -> None:
    """Verify that introspection timestamp is recorded."""
    result = provider.introspect(
        database_id="test_db",
        connection_config={"path": str(temp_sqlite_db)},
    )
    
    assert result.introspected_at is not None
    assert result.introspected_at.tzinfo is not None  # Should be timezone-aware


def test_sqlite_provider_empty_database(provider: SQLiteIntrospectionProvider) -> None:
    """Verify provider handles empty database correctly."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        empty_db_path = Path(f.name)
    
    try:
        # Create empty database (no tables)
        conn = sqlite3.connect(str(empty_db_path))
        conn.close()
        
        result = provider.introspect(
            database_id="empty_db",
            connection_config={"path": str(empty_db_path)},
        )
        
        assert result.database_id == "empty_db"
        assert len(result.tables) == 0
    finally:
        empty_db_path.unlink()
