"""Query execution agent for approved read-only SQL."""

from __future__ import annotations

from time import perf_counter
from typing import Any
from uuid import uuid4

from text_to_sql_agent.repositories import get_query_execution_repository
from text_to_sql_agent.services.audit_trail import make_agent_event, make_mcp_db_audit_event
from text_to_sql_agent.services.mcp_security_policy import enforce_mcp_sql_policy, validate_mcp_sql_policy


def _resolve_allowed_schemas(connection_config: dict[str, Any]) -> list[str] | None:
    raw = connection_config.get("mcp_allowed_schemas") or connection_config.get("allowed_schemas")
    if raw is None:
        return None
    return [str(item).strip() for item in raw if str(item).strip()]

def is_read_only_query(sql_query: str) -> bool:
    """Return True when SQL satisfies the shared MCP read-only policy."""
    return validate_mcp_sql_policy(sql_query).approved


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

    enforce_mcp_sql_policy(sql_query, connection_config)

    repository = get_query_execution_repository(dialect, connection_config)
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
            allowed_schemas = _resolve_allowed_schemas(connection_config)
            policy_result = validate_mcp_sql_policy(sql, allowed_schemas=allowed_schemas)
            request_metadata = {
                "request_id": f"mcp-exec-{uuid4().hex}",
                "tool_name": "mcp.db.execute",
                "database_id": state.get("database_id"),
                "dialect": state.get("dialect", "sqlite"),
                "timeout_ms": int(connection_config.get("timeout_ms", 30000)),
                "row_limit": connection_config.get("row_limit"),
            }
            started_at = perf_counter()
            result = execute_approved_query(
                database_id=state["database_id"],
                dialect=state.get("dialect", "sqlite"),
                sql_query=sql,
                connection_config=connection_config,
            )
            latency_ms = int(result.get("elapsed_ms") or (perf_counter() - started_at) * 1000)
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
                    ),
                    make_mcp_db_audit_event(
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        request_metadata=request_metadata,
                        execution_status="ok",
                        latency_ms=latency_ms,
                        row_count=result.get("row_count"),
                        policy_decision={
                            "approved": policy_result.approved,
                            "violations": policy_result.violations,
                            "referenced_schemas": policy_result.referenced_schemas,
                        },
                    ),
                ],
            }
        except Exception as exc:  # noqa: BLE001
            latency_ms = None
            if "started_at" in locals():
                latency_ms = int((perf_counter() - started_at) * 1000)

            if "request_metadata" not in locals():
                request_metadata = {
                    "request_id": f"mcp-exec-{uuid4().hex}",
                    "tool_name": "mcp.db.execute",
                    "database_id": state.get("database_id"),
                    "dialect": state.get("dialect", "sqlite"),
                    "timeout_ms": int(connection_config.get("timeout_ms", 30000)),
                    "row_limit": connection_config.get("row_limit"),
                }

            if "policy_result" in locals():
                policy_decision = {
                    "approved": policy_result.approved,
                    "violations": policy_result.violations,
                    "referenced_schemas": policy_result.referenced_schemas,
                }
            else:
                policy_decision = {
                    "approved": False,
                    "violations": ["policy_unavailable"],
                    "referenced_schemas": [],
                }

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
                    ),
                    make_mcp_db_audit_event(
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        request_metadata=request_metadata,
                        execution_status="error",
                        latency_ms=latency_ms,
                        policy_decision=policy_decision,
                        error_message=str(exc),
                    ),
                ],
            }

    return node
