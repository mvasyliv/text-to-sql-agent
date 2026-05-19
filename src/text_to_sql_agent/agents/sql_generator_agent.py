"""SQL generator agent for read-only query synthesis.

Builds deterministic SQL from:
- user natural-language question
- formatted schema context from schema_context_agent

The agent intentionally avoids write operations and emits only SELECT queries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from text_to_sql_agent.services.audit_trail import make_agent_event


_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_COUNT_HINTS = {"count", "how", "many", "total", "number"}
_LIST_HINTS = {"list", "show", "all", "display", "give", "find", "get"}


@dataclass(frozen=True, slots=True)
class SQLGenerationResult:
    """Structured output of SQL generation."""

    sql: str
    rationale: str
    table_used: str | None
    intent: str


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _quote_identifier(name: str, dialect: str) -> str:
    """Quote SQL identifiers safely for supported dialects."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")

    # SQLite and PostgreSQL accept ANSI double-quote escaping.
    if dialect in {"sqlite", "postgres", "postgresql"}:
        return f'"{name}"'
    return name


def _parse_schema_context(schema_context: str) -> dict[str, list[str]]:
    """Parse TABLE/COLUMN lines from formatted schema context text."""
    tables: dict[str, list[str]] = {}
    current_table: str | None = None

    for raw_line in schema_context.splitlines():
        line = raw_line.strip()
        if line.startswith("TABLE "):
            table_name = line.removeprefix("TABLE ").strip()
            if table_name:
                current_table = table_name
                tables.setdefault(current_table, [])
            continue

        if current_table is None:
            continue

        # Column lines are formatted like: "  id integer [PK]"
        if line and not line.startswith("FK:"):
            col_name = line.split(" ", 1)[0].strip()
            if _IDENTIFIER_RE.match(col_name):
                tables[current_table].append(col_name)

    return tables


def _choose_table(question_tokens: list[str], schema_map: dict[str, list[str]]) -> str | None:
    if not schema_map:
        return None

    for table in schema_map:
        low = table.lower()
        singular = low[:-1] if low.endswith("s") else low
        if low in question_tokens or singular in question_tokens:
            return table

    return next(iter(schema_map))


def _detect_intent(tokens: list[str]) -> str:
    if any(token in _COUNT_HINTS for token in tokens):
        return "count"
    if any(token in _LIST_HINTS for token in tokens):
        return "list"
    return "list"


def generate_read_only_sql(
    user_question: str,
    schema_context: str,
    *,
    dialect: str = "sqlite",
    max_limit: int = 100,
) -> SQLGenerationResult:
    """Generate a read-only SQL query from question + schema context.

    The generator is deterministic and intentionally conservative for MVP.
    """
    if max_limit <= 0:
        raise ValueError("max_limit must be greater than zero")

    tokens = _tokenize(user_question)
    schema_map = _parse_schema_context(schema_context)
    table = _choose_table(tokens, schema_map)
    intent = _detect_intent(tokens)

    if table is None:
        return SQLGenerationResult(
            sql="SELECT 1 AS result LIMIT 1",
            rationale="No tables were detected in schema context; returning safe probe query.",
            table_used=None,
            intent="probe",
        )

    quoted_table = _quote_identifier(table, dialect)

    if intent == "count":
        sql = f"SELECT COUNT(*) AS row_count FROM {quoted_table}"
        rationale = f"Detected counting intent; counting rows in table '{table}'."
    else:
        sql = f"SELECT * FROM {quoted_table} LIMIT {max_limit}"
        rationale = (
            f"Detected listing intent; selecting rows from table '{table}' "
            f"with LIMIT {max_limit} for safe preview."
        )

    return SQLGenerationResult(
        sql=sql,
        rationale=rationale,
        table_used=table,
        intent=intent,
    )


def build_sql_generator_node(*, max_limit: int = 100):
    """Return a LangGraph-compatible SQL generator node."""

    def node(state: dict) -> dict:
        question = state["user_question"]
        schema_context = state.get("schema_context") or ""
        dialect = state.get("dialect", "sqlite")
        try:
            result = generate_read_only_sql(
                question,
                schema_context,
                dialect=dialect,
                max_limit=max_limit,
            )
            return {
                "generated_sql": result.sql,
                "sql_rationale": result.rationale,
                "status": "validating",
                "log_messages": [
                    "sql_generator: SQL generated"
                    f" (intent={result.intent}, table={result.table_used})"
                ],
                "agent_events": [
                    make_agent_event(
                        agent="sql_generator",
                        event_type="sql_generated",
                        status="ok",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"intent": result.intent, "table_used": result.table_used},
                    )
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "generated_sql": None,
                "sql_rationale": None,
                "status": "failed",
                "error_message": f"sql_generator: failed to generate SQL - {exc}",
                "log_messages": [f"sql_generator: ERROR - {exc}"],
                "agent_events": [
                    make_agent_event(
                        agent="sql_generator",
                        event_type="sql_generated",
                        status="error",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"error": str(exc)},
                    )
                ],
            }

    return node
