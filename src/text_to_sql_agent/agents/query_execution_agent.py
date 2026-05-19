"""Query execution agent for approved read-only SQL."""

from __future__ import annotations

from typing import Any

from text_to_sql_agent.repositories import get_query_execution_repository
from text_to_sql_agent.services.audit_trail import make_agent_event

_ALLOWED_PREFIXES = ("select", "with", "explain")


def is_read_only_query(sql_query: str) -> bool:
    """Return True when SQL starts with a read-only statement prefix."""
    first = sql_query.strip().lower().lstrip("(")
    return any(first.startswith(prefix) for prefix in _ALLOWED_PREFIXES)


def execute_approved_query(
    *,
    database_id: str,
    dialect: str,
    sql_query: str,
    connection_config: dict[str, Any],
) -> dict[str, Any]:
    """Execute approved SQL through repository selected by dialect."""
    if not sql_query.strip():
        raise ValueError("SQL query is empty")
    if not is_read_only_query(sql_query):
        raise ValueError("Only read-only SQL statements are allowed")

    repository = get_query_execution_repository(dialect)
    payload = repository.execute_read_only(database_id, sql_query, connection_config)
    payload["sql"] = sql_query
    payload["dialect"] = dialect
    return payload


def build_query_execution_node(connection_config: dict[str, Any] | None = None):
    """Return a LangGraph-compatible query execution node."""

    def node(state: dict) -> dict:
        sql = (state.get("edited_sql") or state.get("generated_sql") or "").strip()
        if not sql:
            return {
                "execution_result": None,
                "execution_error": "query_executor: SQL is empty",
                "status": "failed",
                "log_messages": ["query_executor: ERROR - SQL is empty"],
            }

        if connection_config is None:
            # Fallback used by graph tests and local dry-runs without DB wiring.
            return {
                "execution_result": {
                    "database_id": state.get("database_id"),
                    "dialect": state.get("dialect", "sqlite"),
                    "sql": sql,
                    "rows": [],
                    "columns": [],
                    "row_count": 0,
                    "metadata": {"mode": "stub"},
                },
                "execution_error": None,
                "status": "post_processing",
                "log_messages": ["query_executor: query executed (stub mode)"],
                "agent_events": [
                    make_agent_event(
                        agent="query_executor",
                        event_type="query_executed",
                        status="ok",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"mode": "stub", "row_count": 0},
                    )
                ],
            }

        try:
            result = execute_approved_query(
                database_id=state["database_id"],
                dialect=state.get("dialect", "sqlite"),
                sql_query=sql,
                connection_config=connection_config,
            )
            return {
                "execution_result": result,
                "execution_error": None,
                "status": "post_processing",
                "log_messages": [
                    "query_executor: query executed"
                    f" rows={result.get('row_count', 0)}"
                ],
                "agent_events": [
                    make_agent_event(
                        agent="query_executor",
                        event_type="query_executed",
                        status="ok",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={
                            "database_id": state.get("database_id"),
                            "dialect": state.get("dialect", "sqlite"),
                            "row_count": result.get("row_count", 0),
                        },
                    )
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "execution_result": None,
                "execution_error": str(exc),
                "status": "failed",
                "error_message": f"query_executor: failed - {exc}",
                "log_messages": [f"query_executor: ERROR - {exc}"],
                "agent_events": [
                    make_agent_event(
                        agent="query_executor",
                        event_type="query_executed",
                        status="error",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"error": str(exc)},
                    )
                ],
            }

    return node
