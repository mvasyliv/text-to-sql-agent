"""Tests for the schema reader agent entrypoint."""

from text_to_sql_agent.agents import SchemaReaderAgent, build_initial_schema_read_state
from text_to_sql_agent.models import SchemaRefreshRequest


class RecordingGraph:
    def __init__(self) -> None:
        self.invocations: list[dict[str, object]] = []

    def invoke(self, state: dict[str, object]) -> dict[str, object]:
        self.invocations.append(state)
        return {
            **state,
            "status": "done",
            "current_node": "complete_schema_ingestion",
            "completed_at": "2026-05-18T12:00:00Z",
        }


def test_build_initial_schema_read_state_maps_request_fields() -> None:
    request = SchemaRefreshRequest(
        database_id="warehouse",
        refresh_mode="incremental",
        target_tables=["orders", "customers"],
        force=True,
    )

    state = build_initial_schema_read_state(
        request,
        request_id="req-123",
        connection_config_ref="env:DATABASE_URL",
    )

    assert state["request_id"] == "req-123"
    assert state["database_id"] == "warehouse"
    assert state["refresh_mode"] == "incremental"
    assert state["target_tables"] == ["orders", "customers"]
    assert state["force_refresh"] is True
    assert state["connection_config_ref"] == "env:DATABASE_URL"
    assert state["status"] == "pending"
    assert state["retry_count"] == 0


def test_schema_reader_agent_invokes_graph_with_initial_state() -> None:
    request = SchemaRefreshRequest(database_id="warehouse", refresh_mode="full")
    graph = RecordingGraph()
    agent = SchemaReaderAgent(graph=graph, request_id_factory=lambda req: "req-fixed")

    result = agent.run(
        request,
        connection_config_ref="config:warehouse.primary",
    )

    assert len(graph.invocations) == 1
    assert graph.invocations[0]["request_id"] == "req-fixed"
    assert graph.invocations[0]["connection_config_ref"] == "config:warehouse.primary"
    assert graph.invocations[0]["database_id"] == "warehouse"
    assert result["status"] == "done"
    assert result["current_node"] == "complete_schema_ingestion"


def test_schema_reader_agent_allows_explicit_request_id_override() -> None:
    request = SchemaRefreshRequest(database_id="warehouse")
    graph = RecordingGraph()
    agent = SchemaReaderAgent(graph=graph)

    agent.run(
        request,
        connection_config_ref="env:DATABASE_URL",
        request_id="req-explicit",
    )

    assert graph.invocations[0]["request_id"] == "req-explicit"
