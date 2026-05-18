"""PostgreSQL schema introspection provider (T-2026-05-15-026)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras

from text_to_sql_agent.models.introspection import (
    RawColumnMeta,
    RawForeignKeyMeta,
    RawIndexMeta,
    RawIntrospectionResult,
    RawTableMeta,
)

from .introspection_provider import SchemaIntrospectionProvider


class PostgresIntrospectionProvider(SchemaIntrospectionProvider):
    """Concrete introspection provider for PostgreSQL databases."""

    def introspect(
        self, database_id: str, connection_config: dict[str, Any]
    ) -> RawIntrospectionResult:
        """Introspect a PostgreSQL database schema.

        Args:
            database_id: Unique identifier for the database.
            connection_config: Connection parameters including:
                - host: PostgreSQL server hostname (required)
                - port: PostgreSQL server port (default 5432)
                - database: Database name (required)
                - username: PostgreSQL user (required)
                - password: PostgreSQL password (required)
                - extra_params: Additional connection parameters (optional)

        Returns:
            RawIntrospectionResult with PostgreSQL schema metadata.

        Raises:
            ConnectionError: If connection to PostgreSQL fails.
            ValueError: If required connection_config keys are missing.
            psycopg2.Error: On SQL query errors.
        """
        # Validate required configuration
        required_keys = ["host", "database", "username", "password"]
        missing_keys = [k for k in required_keys if k not in connection_config]
        if missing_keys:
            raise ValueError(f"Missing required config keys: {', '.join(missing_keys)}")

        host = connection_config["host"]
        port = connection_config.get("port", 5432)
        database = connection_config["database"]
        username = connection_config["username"]
        password = connection_config["password"]
        extra_params = connection_config.get("extra_params", {})

        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                **extra_params,
            )
        except psycopg2.OperationalError as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Query tables and views (excluding system schemas)
            cursor.execute(
                """
                SELECT table_name, table_schema, table_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_internal')
                ORDER BY table_schema, table_name
                """
            )
            table_rows = cursor.fetchall()

            tables: list[RawTableMeta] = []
            for table_row in table_rows:
                table_name = table_row["table_name"]
                schema_name = table_row["table_schema"]
                table_type = table_row["table_type"]

                # Get columns for this table
                columns = self._get_columns(cursor, schema_name, table_name)

                # Get foreign keys for this table
                foreign_keys = self._get_foreign_keys(cursor, schema_name, table_name)

                # Get indexes for this table
                indexes = self._get_indexes(cursor, schema_name, table_name)

                table = RawTableMeta(
                    name=table_name,
                    table_type=table_type,
                    columns=columns,
                    foreign_keys=foreign_keys,
                    indexes=indexes,
                    schema_name=schema_name,
                )
                tables.append(table)

            introspected_at = datetime.now(tz=timezone.utc)
            result = RawIntrospectionResult(
                database_id=database_id,
                dialect="postgresql",
                introspected_at=introspected_at,
                tables=tables,
            )
            return result

        finally:
            conn.close()

    def _get_columns(
        self, cursor: psycopg2.extras.RealDictCursor, schema_name: str, table_name: str
    ) -> list[RawColumnMeta]:
        """Get column metadata for a table."""
        columns: list[RawColumnMeta] = []

        cursor.execute(
            """
            SELECT 
                column_name, 
                data_type,
                is_nullable,
                column_default,
                ordinal_position,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema_name, table_name),
        )
        column_rows = cursor.fetchall()

        # Query for primary key columns
        primary_key_columns = self._get_primary_key_columns(cursor, schema_name, table_name)

        # Query for unique columns
        unique_columns = self._get_unique_columns(cursor, schema_name, table_name)

        for col_row in column_rows:
            col_name = col_row["column_name"]
            col_type = col_row["data_type"]
            is_nullable = col_row["is_nullable"] == "YES"
            default_value = col_row["column_default"]
            ordinal_position = col_row["ordinal_position"]
            char_max_len = col_row["character_maximum_length"]
            numeric_prec = col_row["numeric_precision"]
            numeric_scale = col_row["numeric_scale"]

            col = RawColumnMeta(
                name=col_name,
                data_type=col_type,
                is_nullable=is_nullable,
                is_primary_key=col_name in primary_key_columns,
                is_unique=col_name in unique_columns,
                ordinal_position=ordinal_position,
                default_value=default_value,
                character_maximum_length=char_max_len,
                numeric_precision=numeric_prec,
                numeric_scale=numeric_scale,
            )
            columns.append(col)

        return columns

    def _get_primary_key_columns(
        self, cursor: psycopg2.extras.RealDictCursor, schema_name: str, table_name: str
    ) -> set[str]:
        """Get the set of primary key column names for a table."""
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = %s 
              AND table_name = %s 
              AND constraint_name = (
                SELECT constraint_name 
                FROM information_schema.table_constraints
                WHERE table_schema = %s 
                  AND table_name = %s 
                  AND constraint_type = 'PRIMARY KEY'
              )
            """,
            (schema_name, table_name, schema_name, table_name),
        )
        pk_rows = cursor.fetchall()
        return {row["column_name"] for row in pk_rows}

    def _get_unique_columns(
        self, cursor: psycopg2.extras.RealDictCursor, schema_name: str, table_name: str
    ) -> set[str]:
        """Get the set of unique column names for a table."""
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = %s 
              AND table_name = %s 
              AND constraint_name IN (
                SELECT constraint_name 
                FROM information_schema.table_constraints
                WHERE table_schema = %s 
                  AND table_name = %s 
                  AND constraint_type = 'UNIQUE'
              )
            """,
            (schema_name, table_name, schema_name, table_name),
        )
        unique_rows = cursor.fetchall()
        return {row["column_name"] for row in unique_rows}

    def _get_foreign_keys(
        self, cursor: psycopg2.extras.RealDictCursor, schema_name: str, table_name: str
    ) -> list[RawForeignKeyMeta]:
        """Get foreign key metadata for a table."""
        foreign_keys: list[RawForeignKeyMeta] = []

        cursor.execute(
            """
            SELECT 
                constraint_name,
                table_name,
                column_name,
                referenced_table_name,
                referenced_column_name,
                update_rule,
                delete_rule
            FROM (
                SELECT 
                    kcu.constraint_name,
                    kcu.table_name,
                    kcu.column_name,
                    ccu.table_name AS referenced_table_name,
                    ccu.column_name AS referenced_column_name,
                    rc.update_rule,
                    rc.delete_rule
                FROM information_schema.key_column_usage AS kcu
                JOIN information_schema.constraint_column_usage AS ccu 
                  ON ccu.constraint_name = kcu.constraint_name
                JOIN information_schema.referential_constraints AS rc
                  ON rc.constraint_name = kcu.constraint_name
                WHERE kcu.table_schema = %s AND kcu.table_name = %s
            ) AS fk_info
            ORDER BY constraint_name, ordinal_position
            """,
            (schema_name, table_name),
        )
        fk_rows = cursor.fetchall()

        for row in fk_rows:
            fk = RawForeignKeyMeta(
                constraint_name=row["constraint_name"],
                from_table=row["table_name"],
                from_column=row["column_name"],
                to_table=row["referenced_table_name"],
                to_column=row["referenced_column_name"],
                on_update=row["update_rule"],
                on_delete=row["delete_rule"],
            )
            foreign_keys.append(fk)

        return foreign_keys

    def _get_indexes(
        self, cursor: psycopg2.extras.RealDictCursor, schema_name: str, table_name: str
    ) -> list[RawIndexMeta]:
        """Get index metadata for a table."""
        indexes: list[RawIndexMeta] = []

        cursor.execute(
            """
            SELECT 
                indexname,
                tablename,
                indexdef,
                schemaname
            FROM pg_indexes
            WHERE schemaname = %s AND tablename = %s
            """,
            (schema_name, table_name),
        )
        index_rows = cursor.fetchall()

        for row in index_rows:
            index_name = row["indexname"]
            indexdef = row["indexdef"]
            is_unique = "UNIQUE" in indexdef.upper()

            # Extract column names from the index definition
            # indexdef typically looks like: CREATE [UNIQUE] INDEX idx_name ON schema.table (col1, col2, ...)
            # We'll parse the parentheses content
            columns = self._parse_index_columns(indexdef)

            idx = RawIndexMeta(
                index_name=index_name,
                table_name=table_name,
                columns=columns,
                is_unique=is_unique,
                index_type="BTREE",  # PostgreSQL default, could be HASH, GiST, GIN, etc.
            )
            indexes.append(idx)

        return indexes

    @staticmethod
    def _parse_index_columns(indexdef: str) -> list[str]:
        """Extract column names from PostgreSQL index definition."""
        # Find the part in parentheses
        start_paren = indexdef.rfind("(")
        end_paren = indexdef.rfind(")")
        if start_paren == -1 or end_paren == -1:
            return []

        columns_str = indexdef[start_paren + 1 : end_paren]
        # Split by comma and clean up (remove spaces, function calls, etc.)
        cols = []
        for col in columns_str.split(","):
            col = col.strip()
            # Handle expressions like "lower(name)" or "col ASC"
            if "(" in col:
                # Skip functional indexes for now
                continue
            # Remove ASC/DESC modifiers
            col = col.split()[0]
            if col:
                cols.append(col)

        return cols
