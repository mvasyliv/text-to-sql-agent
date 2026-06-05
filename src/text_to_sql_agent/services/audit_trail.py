"""Audit-trail service: factory helpers and state-to-trail assembly."""

from __future__ import annotations

from typing import Any

from text_to_sql_agent.models.trace import (
    AgentEvent,
    AgentEventStatus,
    AgentEventType,
    AuditTrail,
)


def make_agent_event(
    *,
    agent: str,
    event_type: AgentEventType,
    status: AgentEventStatus,
    user_id: str | None = None,
    conversation_id: str | None = None,
    message_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a serialised agent event dict ready for QueryState.

    Returns a plain dict (not an AgentEvent instance) so that LangGraph
    can serialise it through its JSON checkpoint layer without custom codec.
    """
    event = AgentEvent(
        agent=agent,
        event_type=event_type,
        status=status,
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=message_id,
        metadata=metadata or {},
    )
    return event.model_dump()


def make_mcp_db_audit_event(
    *,
    user_id: str | None,
    conversation_id: str | None,
    message_id: str | None,
    request_metadata: dict[str, Any],
    execution_status: AgentEventStatus,
    latency_ms: int | None,
    policy_decision: dict[str, Any],
    row_count: int | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Create a structured MCP DB operation audit event.

    The event is emitted into ``agent_events`` and consumed by existing trace
    outputs through ``build_audit_trail``.
    """
    metadata: dict[str, Any] = {
        "request": request_metadata,
        "execution": {
            "status": execution_status,
            "latency_ms": latency_ms,
            "row_count": row_count,
        },
        "policy": policy_decision,
    }
    if error_message is not None:
        metadata["execution"]["error_message"] = error_message

    return make_agent_event(
        agent="query_executor",
        event_type="mcp_db_operation",
        status=execution_status,
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=message_id,
        metadata=metadata,
    )


def build_audit_trail(state: dict[str, Any]) -> AuditTrail:
    """Assemble an AuditTrail from a completed (or partial) QueryState dict.

    Reconstructs AgentEvent objects from the raw dicts stored in
    ``state["agent_events"]`` and attaches user/conversation identity.
    """
    raw_events: list[dict[str, Any]] = state.get("agent_events") or []
    events = [AgentEvent.model_validate(e) for e in raw_events]
    return AuditTrail(
        user_id=state.get("user_id"),
        conversation_id=state.get("conversation_id"),
        message_id=state.get("message_id"),
        events=events,
    )
