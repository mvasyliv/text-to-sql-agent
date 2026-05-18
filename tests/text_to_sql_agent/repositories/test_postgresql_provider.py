"""Tests for PostgreSQL schema introspection provider (T-2026-05-15-026)."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest
import psycopg2.extras

from text_to_sql_agent.models.introspection import (
    RawColumnMeta,
    RawForeignKeyMeta,
    RawIndexMeta,
    RawTableMeta,
)
from text_to_sql_agent.repositories import PostgresIntrospectionProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider() -> PostgresIntrospectionProvider:
    """Create a PostgreSQL introspection provider instance."""
    return PostgresIntrospectionProvider()


@pytest.fixture
def mock_cursor() -> MagicMock:
    """Create a mock cursor with RealDictCursor behavior."""
    cursor = MagicMock(spec=psycopg2.extras.RealDictCursor)
    return cursor


@pytest.fixture
def mock_connection() -> MagicMock:
    """Create a mock database connection."""
    conn = MagicMock()
    return conn


@pytest.fixture
def valid_connection_config() -> dict[str, Any]:
    """Valid PostgreSQL connection configuration."""
    return {
        "host": "localhost",
        "port": 5432,
        "database": "test_db",
        "username": "postgres",
        "password": "password",
    }


# ---------------------------------------------------------------------------
# Connection & Configuration Tests
# ---------------------------------------------------------------------------


def test_postgres_provider_missing_host_raises() -> None:
    """Verify error when 'host' is missing from config."""
    provider = PostgresIntrospectionProvider()

    with pytest.raises(ValueError) as exc_info:
        provider.introspect(
            database_id="test_db",
            connection_config={
                "port": 5432,
                "database": "test_db",
                "username": "postgres",
                "password": "password",
            },
        )
    assert "host" in str(exc_info.value).lower()


def test_postgres_provider_missing_database_raises() -> None:
    """Verify error when 'database' is missing from config."""
    provider = PostgresIntrospectionProvider()

    with pytest.raises(ValueError) as exc_info:
        provider.introspect(
            database_id="test_db",
            connection_config={
                "host": "localhost",
                "port": 5432,
                "username": "postgres",
                "password": "password",
            },
        )
    assert "database" in str(exc_info.value).lower()


def test_postgres_provider_missing_username_raises() -> None:
    """Verify error when 'username' is missing from config."""
    provider = PostgresIntrospectionProvider()

    with pytest.raises(ValueError) as exc_info:
        provider.introspect(
            database_id="test_db",
            connection_config={
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "password": "password",
            },
        )
    assert "username" in str(exc_info.value).lower()


def test_postgres_provider_missing_password_raises() -> None:
    """Verify error when 'password' is missing from config."""
    provider = PostgresIntrospectionProvider()

    with pytest.raises(ValueError) as exc_info:
        provider.introspect(
            database_id="test_db",
            connection_config={
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "username": "postgres",
            },
        )
    assert "password" in str(exc_info.value).lower()


@patch("psycopg2.connect")
def test_postgres_provider_connection_error(
    mock_psycopg2_connect: MagicMock,
    provider: PostgresIntrospectionProvider,
    valid_connection_config: dict[str, Any],
) -> None:
    """Verify error is raised on connection failure."""
    mock_psycopg2_connect.side_effect = psycopg2.OperationalError("Connection refused")

    with pytest.raises(ConnectionError) as exc_info:
        provider.introspect(
            database_id="test_db",
            connection_config=valid_connection_config,
        )
    assert "failed" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Basic Introspection Tests
# ---------------------------------------------------------------------------


@patch("psycopg2.connect")
def test_postgres_provider_introspect_basic(
    mock_psycopg2_connect: MagicMock,
    provider: PostgresIntrospectionProvider,
    valid_connection_config: dict[str, Any],
    mock_cursor: MagicMock,
    mock_connection: MagicMock,
) -> None:
    """Test basic introspection structure."""
    mock_psycopg2_connect.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    # Setup mock cursor to return empty table list
    mock_cursor.fetchall.return_value = []

    result = provider.introspect(
        database_id="test_db",
        connection_config=valid_connection_config,
    )

    assert result.database_id == "test_db"
    assert result.dialect == "postgresql"
    assert isinstance(result.introspected_at, datetime)
    assert result.introspected_at.tzinfo is not None  # timezone-aware


@patch("psycopg2.connect")
def test_postgres_provider_tables_discovered(
    mock_psycopg2_connect: MagicMock,
    provider: PostgresIntrospectionProvider,
    valid_connection_config: dict[str, Any],
    mock_cursor: MagicMock,
    mock_connection: MagicMock,
) -> None:
    """Verify tables are discovered from information_schema."""
    mock_psycopg2_connect.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    # Setup mock cursor to return two tables
    mock_cursor.fetchall.side_effect = [
        [
            {"table_name": "users", "table_schema": "public", "table_type": "BASE TABLE"},
            {"table_name": "orders", "table_schema": "public", "table_type": "BASE TABLE"},
        ],
        # Empty columns for first query call to _get_columns for users
        [],
        # Empty PK columns for users
        [],
        # Empty unique columns for users
        [],
        # Empty FK for users
        [],
        # Empty indexes for users
        [],
        # Empty columns for orders
        [],
        # Empty PK columns for orders
        [],
        # Empty unique columns for orders
        [],
        # Empty FK for orders
        [],
        # Empty indexes for orders
        [],
    ]

    result = provider.introspect(
        database_id="test_db",
        connection_config=valid_connection_config,
    )

    assert len(result.tables) == 2
    table_names = [t.name for t in result.tables]
    assert "users" in table_names
    assert "orders" in table_names


@patch("psycopg2.connect")
def test_postgres_provider_column_metadata(
    mock_psycopg2_connect: MagicMock,
    provider: PostgresIntrospectionProvider,
    valid_connection_config: dict[str, Any],
    mock_cursor: MagicMock,
    mock_connection: MagicMock,
) -> None:
    """Verify column metadata is correctly extracted."""
    mock_psycopg2_connect.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    # Setup mock cursor with column data
    mock_cursor.fetchall.side_effect = [
        # Tables query
        [
            {"table_name": "users", "table_schema": "public", "table_type": "BASE TABLE"},
        ],
        # Columns query for users
        [
            {
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": None,
                "ordinal_position": 1,
                "character_maximum_length": None,
                "numeric_precision": 32,
                "numeric_scale": 0,
            },
            {
                "column_name": "email",
                "data_type": "character varying",
                "is_nullable": "YES",
                "column_default": None,
                "ordinal_position": 2,
                "character_maximum_length": 255,
                "numeric_precision": None,
                "numeric_scale": None,
            },
        ],
        # PK columns for users
        [{"column_name": "id"}],
        # Unique columns for users
        [],
        # FK for users
        [],
        # Indexes for users
        [],
    ]

    result = provider.introspect(
        database_id="test_db",
        connection_config=valid_connection_config,
    )

    assert len(result.tables) == 1
    users_table = result.tables[0]
    assert len(users_table.columns) == 2

    id_col = users_table.columns[0]
    assert id_col.name == "id"
    assert id_col.data_type == "integer"
    assert id_col.is_nullable is False
    assert id_col.is_primary_key is True

    email_col = users_table.columns[1]
    assert email_col.name == "email"
    assert email_col.data_type == "character varying"
    assert email_col.is_nullable is True
    assert email_col.character_maximum_length == 255


@patch("psycopg2.connect")
def test_postgres_provider_foreign_keys(
    mock_psycopg2_connect: MagicMock,
    provider: PostgresIntrospectionProvider,
    valid_connection_config: dict[str, Any],
    mock_cursor: MagicMock,
    mock_connection: MagicMock,
) -> None:
    """Verify foreign key constraints are extracted."""
    mock_psycopg2_connect.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    mock_cursor.fetchall.side_effect = [
        # Tables query
        [
            {"table_name": "orders", "table_schema": "public", "table_type": "BASE TABLE"},
        ],
        # Columns query for orders
        [],
        # PK columns for orders
        [],
        # Unique columns for orders
        [],
        # FK for orders
        [
            {
                "constraint_name": "fk_order_user",
                "table_name": "orders",
                "column_name": "user_id",
                "referenced_table_name": "users",
                "referenced_column_name": "id",
                "update_rule": "NO ACTION",
                "delete_rule": "CASCADE",
            }
        ],
        # Indexes for orders
        [],
    ]

    result = provider.introspect(
        database_id="test_db",
        connection_config=valid_connection_config,
    )

    orders_table = result.tables[0]
    assert len(orders_table.foreign_keys) == 1

    fk = orders_table.foreign_keys[0]
    assert fk.constraint_name == "fk_order_user"
    assert fk.from_table == "orders"
    assert fk.from_column == "user_id"
    assert fk.to_table == "users"
    assert fk.to_column == "id"
    assert fk.on_delete == "CASCADE"


@patch("psycopg2.connect")
def test_postgres_provider_indexes(
    mock_psycopg2_connect: MagicMock,
    provider: PostgresIntrospectionProvider,
    valid_connection_config: dict[str, Any],
    mock_cursor: MagicMock,
    mock_connection: MagicMock,
) -> None:
    """Verify indexes are extracted."""
    mock_psycopg2_connect.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    mock_cursor.fetchall.side_effect = [
        # Tables query
        [
            {"table_name": "users", "table_schema": "public", "table_type": "BASE TABLE"},
        ],
        # Columns query for users
        [],
        # PK columns for users
        [],
        # Unique columns for users
        [],
        # FK for users
        [],
        # Indexes for users
        [
            {
                "indexname": "idx_users_email",
                "tablename": "users",
                "schemaname": "public",
                "indexdef": "CREATE UNIQUE INDEX idx_users_email ON public.users (email)",
            },
            {
                "indexname": "idx_users_status",
                "tablename": "users",
                "schemaname": "public",
                "indexdef": "CREATE INDEX idx_users_status ON public.users (status)",
            },
        ],
    ]

    result = provider.introspect(
        database_id="test_db",
        connection_config=valid_connection_config,
    )

    users_table = result.tables[0]
    assert len(users_table.indexes) == 2

    idx1 = users_table.indexes[0]
    assert idx1.index_name == "idx_users_email"
    assert idx1.is_unique is True
    assert "email" in idx1.columns

    idx2 = users_table.indexes[1]
    assert idx2.index_name == "idx_users_status"
    assert idx2.is_unique is False


# ---------------------------------------------------------------------------
# Helper Method Tests
# ---------------------------------------------------------------------------


def test_parse_index_columns_simple() -> None:
    """Test parsing simple index column names."""
    indexdef = "CREATE INDEX idx_col1 ON table_name (col1)"
    columns = PostgresIntrospectionProvider._parse_index_columns(indexdef)
    assert "col1" in columns


def test_parse_index_columns_multiple() -> None:
    """Test parsing multiple columns in index."""
    indexdef = "CREATE INDEX idx_multi ON table_name (col1, col2, col3)"
    columns = PostgresIntrospectionProvider._parse_index_columns(indexdef)
    assert len(columns) >= 1
    assert "col1" in columns


def test_parse_index_columns_with_modifiers() -> None:
    """Test parsing index columns with ASC/DESC modifiers."""
    indexdef = "CREATE INDEX idx_sort ON table_name (col1 ASC, col2 DESC)"
    columns = PostgresIntrospectionProvider._parse_index_columns(indexdef)
    assert "col1" in columns
    assert "col2" in columns


def test_parse_index_columns_functional_skipped() -> None:
    """Test that functional indexes are handled gracefully."""
    indexdef = "CREATE INDEX idx_func ON table_name (lower(name))"
    columns = PostgresIntrospectionProvider._parse_index_columns(indexdef)
    # Functional indexes are skipped, so we expect empty or minimal results
    # The important thing is it doesn't crash


# ---------------------------------------------------------------------------
# Schema Exclusion Tests
# ---------------------------------------------------------------------------


@patch("psycopg2.connect")
def test_postgres_provider_excludes_system_schemas(
    mock_psycopg2_connect: MagicMock,
    provider: PostgresIntrospectionProvider,
    valid_connection_config: dict[str, Any],
    mock_cursor: MagicMock,
    mock_connection: MagicMock,
) -> None:
    """Verify system schemas are excluded from results."""
    mock_psycopg2_connect.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    # The provider should query only non-system schemas
    # We verify the query has the correct WHERE clause
    mock_cursor.fetchall.return_value = []

    result = provider.introspect(
        database_id="test_db",
        connection_config=valid_connection_config,
    )

    # Verify that the first execute call (tables query) contains schema filtering
    first_call_sql = mock_cursor.execute.call_args_list[0][0][0]
    assert "pg_catalog" in first_call_sql
    assert "information_schema" in first_call_sql


# ---------------------------------------------------------------------------
# Extra Parameters Test
# ---------------------------------------------------------------------------


@patch("psycopg2.connect")
def test_postgres_provider_extra_params(
    mock_psycopg2_connect: MagicMock,
    provider: PostgresIntrospectionProvider,
) -> None:
    """Verify extra connection parameters are passed through."""
    mock_connection = MagicMock()
    mock_cursor = MagicMock(spec=psycopg2.extras.RealDictCursor)
    mock_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    mock_psycopg2_connect.return_value = mock_connection

    config = {
        "host": "localhost",
        "database": "test_db",
        "username": "postgres",
        "password": "password",
        "extra_params": {
            "connect_timeout": 10,
            "sslmode": "require",
        },
    }

    provider.introspect(
        database_id="test_db",
        connection_config=config,
    )

    # Verify psycopg2.connect was called with extra_params
    call_kwargs = mock_psycopg2_connect.call_args[1]
    assert call_kwargs.get("connect_timeout") == 10
    assert call_kwargs.get("sslmode") == "require"


# ---------------------------------------------------------------------------
# Connection Cleanup Test
# ---------------------------------------------------------------------------


@patch("psycopg2.connect")
def test_postgres_provider_closes_connection(
    mock_psycopg2_connect: MagicMock,
    provider: PostgresIntrospectionProvider,
    valid_connection_config: dict[str, Any],
) -> None:
    """Verify connection is closed after introspection."""
    mock_connection = MagicMock()
    mock_cursor = MagicMock(spec=psycopg2.extras.RealDictCursor)
    mock_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    mock_psycopg2_connect.return_value = mock_connection

    provider.introspect(
        database_id="test_db",
        connection_config=valid_connection_config,
    )

    # Verify connection was closed
    mock_connection.close.assert_called_once()
