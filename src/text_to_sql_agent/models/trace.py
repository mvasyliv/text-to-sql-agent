"""Structured trace and audit-trail models for agent-run observability."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentEventType = Literal[
    "schema_context_loaded",
    "sql_generated",
    "syntax_validated",
    "security_checked",
    "human_approval",
    "query_executed",
    "analytics_computed",
    "insight_generated",
    "export_completed",
    "workflow_done",
    "workflow_failed",
]

AgentEventStatus = Literal["ok", "error", "warning", "pending"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentEvent(BaseModel):
    """A single structured trace entry emitted by one pipeline node."""

    timestamp: str = Field(default_factory=_utc_now_iso)
    """ISO 8601 UTC timestamp when the event was recorded."""

    agent: str
    """Name of the pipeline node that produced this event."""

    event_type: AgentEventType
    """Semantic category of the event."""

    status: AgentEventStatus
    """Outcome of the operation: ok, error, warning, or pending."""

    user_id: str | None = None
    """User who initiated the workflow, for compliance linkage."""

    conversation_id: str | None = None
    """Conversation this workflow belongs to."""

    message_id: str | None = None
    """Triggering user message."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Arbitrary key/value pairs specific to the event type."""


class AuditTrail(BaseModel):
    """Ordered sequence of agent events for one query workflow run."""

    user_id: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    events: list[AgentEvent] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Return True if any event recorded an error status."""
        return any(e.status == "error" for e in self.events)

    def events_by_agent(self, agent: str) -> list[AgentEvent]:
        """Return all events emitted by the named agent."""
        return [e for e in self.events if e.agent == agent]
