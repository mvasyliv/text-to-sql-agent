"""Schema context agent: prepares normalized schema context for SQL generation.

Reads the database schema via the existing introspection/normalization stack
and formats it into a compact text representation that the SQL generator agent
can use as context when producing queries.

The agent is intentionally stateless: it receives database connection config
and returns a formatted string. Integration into the LangGraph query workflow
is done by wiring `build_schema_context_node()` into the orchestration graph.
"""

from __future__ import annotations

from text_to_sql_agent.models.schema import ColumnSchema, DatabaseSchema, TableSchema
from text_to_sql_agent.repositories.provider_factory import get_introspection_provider
from text_to_sql_agent.services.audit_trail import make_agent_event
from text_to_sql_agent.services.schema_normalization import normalize_raw_schema

# Words that should be skipped when the caller passes a table allowlist
_SCHEMA_STOPWORDS = {"table", "tables", "the", "for", "of", "a", "an", "and"}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_column(col: ColumnSchema) -> str:
    tags: list[str] = []
    if col.is_primary_key:
        tags.append("PK")
    if col.is_foreign_key:
        tags.append("FK")
    if not col.is_nullable:
        tags.append("NOT NULL")
    tag_str = f" [{', '.join(tags)}]" if tags else ""
    return f"  {col.name} {col.data_type}{tag_str}"


def _format_table(table: TableSchema) -> str:
    lines = [f"TABLE {table.name}"]
    for col in table.columns:
        lines.append(_format_column(col))
    if table.foreign_keys:
        for fk in table.foreign_keys:
            lines.append(f"  FK: {fk.from_column} -> {fk.to_table}.{fk.to_column}")
    return "\n".join(lines)


def format_schema_context(schema: DatabaseSchema, table_filter: list[str] | None = None) -> str:
    """Format a DatabaseSchema into a compact text block for LLM context.

    Args:
        schema: Normalised database schema.
        table_filter: Optional list of table names to include. When None,
                      all tables are included.

    Returns:
        Multi-line text describing the schema suitable for prompt injection.
    """
    tables = schema.tables
    if table_filter:
        lower_filter = {t.lower().strip("?.!,:;") for t in table_filter
                        if t.lower() not in _SCHEMA_STOPWORDS}
        tables = [t for t in tables if t.name.lower() in lower_filter]

    if not tables:
        return f"-- No tables found in database '{schema.database_id}'"

    header = f"-- Database: {schema.database_id} ({schema.dialect})"
    body = "\n\n".join(_format_table(t) for t in tables)
    return f"{header}\n\n{body}"


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------


def build_schema_context(
    database_id: str,
    connection_config: dict,
    dialect: str = "sqlite",
    table_filter: list[str] | None = None,
) -> str:
    """Introspect the target database and return a formatted schema context string.

    Args:
        database_id: Logical database identifier.
        connection_config: Dict passed to the introspection provider
                           (e.g. {"path": "/data/db.sqlite"}).
        dialect: SQL dialect string used to select the correct provider.
        table_filter: Optional list of table names to restrict output.

    Returns:
        Formatted schema context string ready for prompt injection.
    """
    provider = get_introspection_provider(dialect)
    raw = provider.introspect(database_id, connection_config)
    schema = normalize_raw_schema(raw)
    return format_schema_context(schema, table_filter)


# ---------------------------------------------------------------------------
# LangGraph node adapter
# ---------------------------------------------------------------------------


def build_schema_context_node(connection_config: dict) -> callable:
    """Return a LangGraph-compatible node function bound to connection_config.

    Usage in query_graph.py:
        from text_to_sql_agent.agents.schema_context_agent import build_schema_context_node
        builder.add_node("schema_context", build_schema_context_node({"path": DB_PATH}))

    Args:
        connection_config: Connection parameters for the introspection provider.

    Returns:
        A node function with signature (state: QueryState) -> dict.
    """

    def node(state: dict) -> dict:
        database_id = state["database_id"]
        dialect = state.get("dialect", "sqlite")
        selected_tables = state.get("selected_tables")
        try:
            context = build_schema_context(
                database_id,
                connection_config,
                dialect,
                table_filter=selected_tables,
            )
            return {
                "schema_context": context,
                "status": "validating",
                "log_messages": [
                    f"schema_context: schema loaded for database '{database_id}' ({dialect})"
                ],
                "agent_events": [
                    make_agent_event(
                        agent="schema_context",
                        event_type="schema_context_loaded",
                        status="ok",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={
                            "database_id": database_id,
                            "dialect": dialect,
                            "selected_tables": selected_tables,
                        },
                    )
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "schema_context": None,
                "status": "failed",
                "error_message": f"schema_context: failed to load schema — {exc}",
                "log_messages": [f"schema_context: ERROR — {exc}"],
                "agent_events": [
                    make_agent_event(
                        agent="schema_context",
                        event_type="schema_context_loaded",
                        status="error",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"database_id": database_id, "error": str(exc)},
                    )
                ],
            }

    return node
