"""Tests for the audit_trail service."""

from text_to_sql_agent.models.trace import AgentEvent, AuditTrail
from text_to_sql_agent.services.audit_trail import build_audit_trail, make_agent_event


class TestMakeAgentEvent:
    def test_returns_plain_dict(self):
        result = make_agent_event(
            agent="sql_generator",
            event_type="sql_generated",
            status="ok",
        )
        assert isinstance(result, dict)
        assert result["agent"] == "sql_generator"
        assert result["event_type"] == "sql_generated"
        assert result["status"] == "ok"

    def test_timestamp_is_populated(self):
        result = make_agent_event(agent="x", event_type="workflow_done", status="ok")
        assert result["timestamp"]

    def test_identity_fields_included(self):
        result = make_agent_event(
            agent="query_executor",
            event_type="query_executed",
            status="ok",
            user_id="u1",
            conversation_id="c1",
            message_id="m1",
            metadata={"row_count": 5},
        )
        assert result["user_id"] == "u1"
        assert result["conversation_id"] == "c1"
        assert result["message_id"] == "m1"
        assert result["metadata"]["row_count"] == 5

    def test_default_metadata_is_empty_dict(self):
        result = make_agent_event(agent="x", event_type="workflow_done", status="ok")
        assert result["metadata"] == {}

    def test_dict_can_be_restored_as_agent_event(self):
        raw = make_agent_event(agent="syntax_validator", event_type="syntax_validated", status="ok")
        event = AgentEvent.model_validate(raw)
        assert event.agent == "syntax_validator"


class TestBuildAuditTrail:
    def _make_raw_event(self, agent: str, event_type: str, status: str) -> dict:
        return make_agent_event(agent=agent, event_type=event_type, status=status)

    def test_empty_state_returns_empty_trail(self):
        trail = build_audit_trail({})
        assert isinstance(trail, AuditTrail)
        assert trail.events == []
        assert trail.user_id is None

    def test_identity_extracted_from_state(self):
        state = {"user_id": "u1", "conversation_id": "c1", "message_id": "m1"}
        trail = build_audit_trail(state)
        assert trail.user_id == "u1"
        assert trail.conversation_id == "c1"
        assert trail.message_id == "m1"

    def test_events_reconstructed_from_dicts(self):
        raw_events = [
            self._make_raw_event("schema_context", "schema_context_loaded", "ok"),
            self._make_raw_event("sql_generator", "sql_generated", "ok"),
            self._make_raw_event("security_guard", "security_checked", "error"),
        ]
        state = {
            "user_id": "u1",
            "conversation_id": "c1",
            "message_id": "m1",
            "agent_events": raw_events,
        }
        trail = build_audit_trail(state)
        assert len(trail.events) == 3
        assert trail.has_errors
        assert trail.events[0].agent == "schema_context"

    def test_missing_agent_events_key_returns_empty_events(self):
        trail = build_audit_trail({"user_id": "u1"})
        assert trail.events == []
