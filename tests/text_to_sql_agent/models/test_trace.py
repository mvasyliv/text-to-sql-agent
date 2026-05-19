"""Tests for AgentEvent and AuditTrail trace models."""

import pytest
from pydantic import ValidationError

from text_to_sql_agent.models.trace import AgentEvent, AuditTrail


class TestAgentEvent:
    def test_minimal_construction(self):
        event = AgentEvent(agent="schema_context", event_type="schema_context_loaded", status="ok")
        assert event.agent == "schema_context"
        assert event.event_type == "schema_context_loaded"
        assert event.status == "ok"
        assert event.timestamp  # auto-populated

    def test_full_construction_with_identity(self):
        event = AgentEvent(
            agent="query_executor",
            event_type="query_executed",
            status="ok",
            user_id="u1",
            conversation_id="c1",
            message_id="m1",
            metadata={"row_count": 42},
        )
        assert event.user_id == "u1"
        assert event.conversation_id == "c1"
        assert event.message_id == "m1"
        assert event.metadata["row_count"] == 42

    def test_invalid_event_type_raises(self):
        with pytest.raises(ValidationError):
            AgentEvent(agent="x", event_type="nonexistent_type", status="ok")

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            AgentEvent(agent="x", event_type="workflow_done", status="unknown_status")

    def test_model_dump_is_serialisable(self):
        event = AgentEvent(
            agent="security_guard",
            event_type="security_checked",
            status="error",
            metadata={"violations": ["non_read_only_entrypoint"]},
        )
        d = event.model_dump()
        assert isinstance(d, dict)
        assert d["agent"] == "security_guard"
        assert d["metadata"]["violations"] == ["non_read_only_entrypoint"]

    def test_model_validate_round_trip(self):
        event = AgentEvent(agent="sql_generator", event_type="sql_generated", status="ok")
        restored = AgentEvent.model_validate(event.model_dump())
        assert restored.agent == event.agent
        assert restored.event_type == event.event_type


class TestAuditTrail:
    def _make_event(self, agent: str, event_type, status: str) -> AgentEvent:
        return AgentEvent(agent=agent, event_type=event_type, status=status)

    def test_empty_trail(self):
        trail = AuditTrail()
        assert trail.events == []
        assert not trail.has_errors

    def test_has_errors_when_error_present(self):
        trail = AuditTrail(
            events=[
                self._make_event("sql_generator", "sql_generated", "ok"),
                self._make_event("security_guard", "security_checked", "error"),
            ]
        )
        assert trail.has_errors

    def test_no_errors_all_ok(self):
        trail = AuditTrail(
            events=[
                self._make_event("sql_generator", "sql_generated", "ok"),
                self._make_event("syntax_validator", "syntax_validated", "ok"),
            ]
        )
        assert not trail.has_errors

    def test_events_by_agent_filters_correctly(self):
        trail = AuditTrail(
            events=[
                self._make_event("sql_generator", "sql_generated", "ok"),
                self._make_event("security_guard", "security_checked", "ok"),
                self._make_event("security_guard", "security_checked", "error"),
            ]
        )
        assert len(trail.events_by_agent("security_guard")) == 2
        assert len(trail.events_by_agent("sql_generator")) == 1
        assert trail.events_by_agent("unknown") == []

    def test_identity_fields_stored(self):
        trail = AuditTrail(user_id="u1", conversation_id="c1", message_id="m1")
        assert trail.user_id == "u1"
        assert trail.conversation_id == "c1"
        assert trail.message_id == "m1"
