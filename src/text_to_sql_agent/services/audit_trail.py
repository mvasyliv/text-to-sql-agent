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
