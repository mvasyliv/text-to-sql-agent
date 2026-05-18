"""Terminal SQL agent — interactive query assistant with schema inspection."""

import json
import os
import sys

from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from loguru import logger

from text_to_sql_agent.config import load_runtime_environment
from text_to_sql_agent.models import DatabaseSchema, TableSchema
from text_to_sql_agent.repositories.sqlite_provider import SQLiteIntrospectionProvider
from text_to_sql_agent.services.schema_normalization import normalize_raw_schema

_runtime_env_result = load_runtime_environment()

# --------------------------------------------------------------------------- #
# Configuration                                                                #
# --------------------------------------------------------------------------- #

_DB_PATH: str = os.getenv("SQLITE_PATH", "database.db")
_DB_ID: str = os.getenv("SQLITE_DB_ID", "default")

# --------------------------------------------------------------------------- #
# Schema helpers                                                               #
# --------------------------------------------------------------------------- #

_provider = SQLiteIntrospectionProvider()


def _load_schema() -> DatabaseSchema:
    raw = _provider.introspect(_DB_ID, {"path": _DB_PATH})
    return normalize_raw_schema(raw)


def _format_table(table: TableSchema) -> str:
    lines = [f"Table: {table.name} ({table.table_type})"]
    lines.append("Columns:")
    for col in table.columns:
        tags: list[str] = []
        if col.is_primary_key:
            tags.append("PK")
        if col.is_foreign_key:
            tags.append("FK")
        if not col.is_nullable:
            tags.append("NOT NULL")
        tag_str = f"  [{', '.join(tags)}]" if tags else ""
        lines.append(f"  {col.name}: {col.data_type}{tag_str}")
    if table.foreign_keys:
        lines.append("Foreign Keys:")
        for fk in table.foreign_keys:
            lines.append(f"  {fk.from_column} -> {fk.to_table}.{fk.to_column}")
    return "\n".join(lines)


def get_db_schema(table_filter: list[str] | None = None) -> str:
    """Return formatted schema for all tables or a filtered subset."""
    try:
        schema = _load_schema()
        tables = schema.tables
        if table_filter:
            lower = {t.lower() for t in table_filter}
            tables = [t for t in tables if t.name.lower() in lower]
            if not tables:
                return f"No tables found matching: {', '.join(table_filter)}"
        if not tables:
            return "No tables found in database."
        header = f"Database: {schema.database_id} ({schema.dialect})\n"
        return header + "\n\n".join(_format_table(t) for t in tables)
    except Exception as exc:
        logger.error("Schema retrieval failed: {}", exc)
        return f"Error retrieving schema: {exc}"


def _get_schema_tool_input(table_names: str = "") -> str:
    """Tool adapter for schema retrieval with optional table filters."""
    raw = table_names.strip()
    if not raw:
        return get_db_schema()
    names = [item for item in raw.replace(",", " ").split() if item]
    return get_db_schema(names or None)


_SCHEMA_COMMAND_STOPWORDS = {"table", "tables", "the", "for", "of", "a", "an", "and"}


def _extract_schema_table_names(text: str) -> list[str]:
    """Extract table names from a schema shortcut while skipping filler words."""
    cleaned = text.strip().replace(",", " ")
    names: list[str] = []
    for token in cleaned.split():
        candidate = token.strip("?.!,:;()[]{}\"'")
        if not candidate:
            continue
        if candidate.lower() in _SCHEMA_COMMAND_STOPWORDS:
            continue
        names.append(candidate)
    return names


# --------------------------------------------------------------------------- #
# Query execution — read-only enforcement                                      #
# --------------------------------------------------------------------------- #

_ALLOWED_PREFIXES = ("select", "explain", "with")


def _is_readonly(sql: str) -> bool:
    first = sql.strip().lower().lstrip("(")
    return any(first.startswith(p) for p in _ALLOWED_PREFIXES)


def query_database(sql_query: str) -> str:
    """Execute a read-only SQL query and return JSON results."""
    import sqlite3

    if not _is_readonly(sql_query):
        return json.dumps({"success": False, "error": "Only SELECT queries are allowed."})
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return json.dumps({"success": True, "results": rows})
    except Exception as exc:
        logger.error("Query failed: {}", exc)
        return json.dumps({"success": False, "error": str(exc)})


# --------------------------------------------------------------------------- #
# Agent setup                                                                  #
# --------------------------------------------------------------------------- #

tools = [
    StructuredTool.from_function(
        name="get_schema",
        func=_get_schema_tool_input,
        description=(
            "Get database schema. Optional input is a space- or comma-separated "
            "list of table names (for example: 'users orders')."
        ),
    ),
    StructuredTool.from_function(
        name="execute_query",
        func=query_database,
        description=(
            "Execute a read-only SELECT query against the database. "
            "Input must be a valid SQL SELECT statement."
        ),
    ),
]

_PROMPT_TEMPLATE = """You are a SQL expert assistant that helps users query their database.

Available tools:
1. get_schema — retrieve the database structure (tables and columns)
2. execute_query — run a read-only SQL SELECT query

When answering questions about the database:
1. Use get_schema to understand the structure when needed.
2. Write appropriate SELECT queries.
3. Use execute_query to fetch results.
4. Explain the results clearly to the user.

Keep responses concise and factual."""


def _resolve_openai_api_key() -> str | None:
    """Resolve OpenAI API key from supported env variable aliases."""
    for key_name in ("OPENAI_API_KEY", "OPENAI_KEY", "OPENAI_TOKEN", "LLM_API_KEY"):
        raw_value = os.getenv(key_name)
        if not raw_value:
            continue
        value = raw_value.strip().strip('"').strip("'")
        if value:
            return value
    return None


def _build_agent(model: str = "gpt-4"):
    api_key = _resolve_openai_api_key()
    if not api_key:
        raise RuntimeError(
            "OpenAI API key is missing. Set OPENAI_API_KEY (or OPENAI_KEY / OPENAI_TOKEN / LLM_API_KEY) "
            "in your shell or .env file."
        )
    llm = ChatOpenAI(
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", model),
        temperature=0,
    )
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=_PROMPT_TEMPLATE,
    )

# --------------------------------------------------------------------------- #
# Main terminal loop                                                           #
# --------------------------------------------------------------------------- #


def main() -> None:
    """Run the interactive terminal SQL agent."""
    logger.configure(handlers=[{"sink": sys.stderr, "level": "WARNING"}])
    for warning in _runtime_env_result.warnings:
        logger.warning(warning)
    print("=" * 60)
    print("SQL Agent Terminal — Database Query Assistant")
    print("=" * 60)
    print(f"\nDatabase: {_DB_PATH}")
    print("\nCommands:")
    print("  schema               — view full database schema")
    print("  schema <t1> [<t2>…]  — view schema for specific tables")
    print("  quit                 — exit")
    print("  <any question>       — ask the AI agent")
    print("-" * 60)

    agent_graph = None

    while True:
        try:
            raw = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd == "quit":
            print("Goodbye!")
            break

        if cmd == "schema":
            table_filter = parts[1:] if len(parts) > 1 else None
            print()
            print(get_db_schema(table_filter))
            continue

        # Support common natural-language schema intents without LLM.
        raw_lower = raw.lower()
        if raw_lower in {
            "view full database schema",
            "show full database schema",
            "show database schema",
            "view database schema",
            "database schema",
            "show schema",
            "view schema",
        }:
            print()
            print(get_db_schema())
            continue
        if raw_lower.startswith("show schema for ") or raw_lower.startswith("view schema for "):
            prefix = "show schema for " if raw_lower.startswith("show schema for ") else "view schema for "
            names = _extract_schema_table_names(raw[len(prefix):])
            print()
            print(get_db_schema(names))
            continue

        # Natural language — delegate to LangChain agent
        if agent_graph is None:
            try:
                agent_graph = _build_agent()
            except Exception as exc:
                print(f"Failed to initialise agent: {exc}")
                print("Tip: use 'schema' or 'schema <table>' to inspect schema without LLM.")
                continue

        print("\nProcessing…")
        try:
            result = agent_graph.invoke({"messages": [("human", raw)]})
            last = result["messages"][-1]
            print("\nAnswer:", getattr(last, "content", str(last)))
        except Exception as exc:
            logger.error("Agent invocation failed: {}", exc)
            print(f"Error: {exc}")

if __name__ == "__main__":
    main()
