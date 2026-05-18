"""SQLite schema introspection provider."""

import sqlite3
from datetime import datetime, timezone
from typing import Any

from text_to_sql_agent.models import (
    RawColumnMeta,
    RawForeignKeyMeta,
    RawIndexMeta,
    RawIntrospectionResult,
    RawTableMeta,
)
from text_to_sql_agent.repositories.introspection_provider import (
    SchemaIntrospectionProvider,
)


class SQLiteIntrospectionProvider(SchemaIntrospectionProvider):
    """SQLite schema introspection using PRAGMA queries and sqlite_master."""

    def introspect(
        self,
        database_id: str,
        connection_config: dict[str, Any],
    ) -> RawIntrospectionResult:
        """Introspect a SQLite database.
        
        Args:
            database_id: Database identifier.
            connection_config: Expected keys:
                - "path": file path to SQLite database (or ":memory:" for in-memory).
                  Required.
        
        Returns:
            RawIntrospectionResult with all tables, columns, FKs, and indexes.
        
        Raises:
            ValueError: If connection_config lacks "path" key.
            sqlite3.Error: If database connection or queries fail.
        """
        db_path = connection_config.get("path")
        if not db_path:
            raise ValueError("SQLite connection_config must include 'path' key")

        tables = []
        warnings = []

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Enable foreign keys to ensure FK constraints are visible
            cursor.execute("PRAGMA foreign_keys = ON")

            # Read all user tables and views from sqlite_master
            cursor.execute(
                """
                SELECT name, type FROM sqlite_master
                WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
            table_rows = cursor.fetchall()

            for table_row in table_rows:
                table_name = table_row["name"]
                table_type = "VIEW" if table_row["type"] == "view" else "TABLE"

                columns = self._get_columns(cursor, table_name)
                foreign_keys = self._get_foreign_keys(cursor, table_name)
                indexes = self._get_indexes(cursor, table_name)

                table_meta = RawTableMeta(
                    name=table_name,
                    table_type=table_type,
                    columns=columns,
                    foreign_keys=foreign_keys,
                    indexes=indexes,
                    schema_name=None,  # SQLite has no schema concept
                    row_count_estimate=None,  # Not easily available without full table scan
                    comment=None,  # SQLite has no table comments
                )
                tables.append(table_meta)

            conn.close()

        except sqlite3.Error as e:
            raise sqlite3.Error(f"SQLite introspection failed for {database_id}: {e}") from e

        return RawIntrospectionResult(
            database_id=database_id,
            dialect="sqlite",
            introspected_at=datetime.now(timezone.utc),
            tables=tables,
            warnings=warnings,
        )

    def _get_columns(self, cursor: sqlite3.Cursor, table_name: str) -> list[RawColumnMeta]:
        """Get column metadata for a table using PRAGMA table_info."""
        columns: list[RawColumnMeta] = []
        cursor.execute(f"PRAGMA table_info({table_name})")
        column_rows = cursor.fetchall()

        for col_row in column_rows:
            # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
            col_name = col_row["name"]
            col_type = col_row["type"]
            is_primary_key = bool(col_row["pk"])
            # In SQLite, primary key columns are implicitly NOT NULL
            is_nullable = not (col_row["notnull"] or is_primary_key)
            default_value = col_row["dflt_value"]
            ordinal_position = col_row["cid"]

            col = RawColumnMeta(
                name=col_name,
                data_type=col_type,
                is_nullable=is_nullable,
                is_primary_key=is_primary_key,
                is_unique=False,  # Not directly available from PRAGMA table_info
                ordinal_position=ordinal_position,
                default_value=default_value,
            )
            columns.append(col)

        return columns

    def _get_foreign_keys(self, cursor: sqlite3.Cursor, table_name: str) -> list[RawForeignKeyMeta]:
        """Get foreign key constraints using PRAGMA foreign_key_list."""
        fks: list[RawForeignKeyMeta] = []
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        fk_rows = cursor.fetchall()

        for fk_row in fk_rows:
            # PRAGMA foreign_key_list columns: id, seq, table, from, to, on_update, on_delete, match
            fk = RawForeignKeyMeta(
                constraint_name=f"{table_name}_fk_{fk_row['id']}",
                from_table=table_name,
                from_column=fk_row["from"],
                to_table=fk_row["table"],
                to_column=fk_row["to"],
                on_update=fk_row["on_update"] if fk_row["on_update"] != "NO ACTION" else None,
                on_delete=fk_row["on_delete"] if fk_row["on_delete"] != "NO ACTION" else None,
            )
            fks.append(fk)

        return fks

    def _get_indexes(self, cursor: sqlite3.Cursor, table_name: str) -> list[RawIndexMeta]:
        """Get indexes for a table using PRAGMA index_list and index_info."""
        indexes: list[RawIndexMeta] = []
        cursor.execute(f"PRAGMA index_list({table_name})")
        index_rows = cursor.fetchall()

        for idx_row in index_rows:
            # PRAGMA index_list columns: seq, name, unique, origin, partial
            index_name = idx_row["name"]
            is_unique = bool(idx_row["unique"])

            # Get columns in this index using PRAGMA index_info
            cursor.execute(f"PRAGMA index_info({index_name})")
            index_info_rows = cursor.fetchall()
            index_columns = [row["name"] for row in index_info_rows]

            idx = RawIndexMeta(
                index_name=index_name,
                table_name=table_name,
                columns=index_columns,
                is_unique=is_unique,
                index_type=None,  # SQLite doesn't expose index type in PRAGMA
            )
            indexes.append(idx)

        return indexes
