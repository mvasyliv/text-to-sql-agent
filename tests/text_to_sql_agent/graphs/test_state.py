"""Tests for LangGraph SchemaReadState (T-2026-05-15-023)."""

from datetime import datetime, timezone
from typing import get_type_hints

import pytest

from text_to_sql_agent.graphs.state import SchemaReadState
from text_to_sql_agent.models import DatabaseSchema, RawIntrospectionResult, RawTableMeta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)


def _minimal_introspection() -> RawIntrospectionResult:
    """Create a minimal introspection result for testing."""
    return RawIntrospectionResult(
        database_id="db-001",
        dialect="sqlite",
        introspected_at=_now(),
        tables=[],
    )


def _create_initial_state(request_id: str = "req-001", database_id: str = "db-001") -> SchemaReadState:
    """Helper to create a valid initial state."""
    return {
        "request_id": request_id,
        "database_id": database_id,
        "dialect": None,
        "refresh_mode": "full",
        "target_tables": None,
        "force_refresh": False,
        "connection_config_ref": "env:DATABASE_URL",
        "introspection_result": None,
        "normalized_schema": None,
        "snapshot_id": None,
        "document_ids": [],
        "embedding_ids": [],
        "status": "pending",
        "current_node": None,
        "retry_count": 0,
        "errors": [],
        "warnings": [],
        "introspected_at": None,
        "completed_at": None,
    }


# ---------------------------------------------------------------------------
# Type definition tests
# ---------------------------------------------------------------------------


def test_schema_read_state_is_typed_dict() -> None:
    """Verify SchemaReadState is a TypedDict."""
    hints = get_type_hints(SchemaReadState)
    assert "request_id" in hints
    assert "database_id" in hints
    assert "status" in hints


def test_schema_read_state_required_fields() -> None:
    """Verify SchemaReadState has all required fields."""
    required_fields = {
        "request_id",
        "database_id",
        "dialect",
        "refresh_mode",
        "target_tables",
        "force_refresh",
        "connection_config_ref",
        "introspection_result",
        "normalized_schema",
        "snapshot_id",
        "document_ids",
        "embedding_ids",
        "status",
        "current_node",
        "retry_count",
        "errors",
        "warnings",
        "introspected_at",
        "completed_at",
    }
    hints = get_type_hints(SchemaReadState)
    for field in required_fields:
        assert field in hints, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# State creation and initialization tests
# ---------------------------------------------------------------------------


def test_create_initial_state() -> None:
    """Verify we can create a valid initial state."""
    state = _create_initial_state()
    assert state["request_id"] == "req-001"
    assert state["status"] == "pending"
    assert state["errors"] == []
    assert state["retry_count"] == 0


def test_state_with_partial_initialization() -> None:
    """Verify we can work with partial state updates."""
    state = _create_initial_state()
    state["status"] = "introspecting"
    state["current_node"] = "introspect_schema"
    assert state["status"] == "introspecting"
    assert state["current_node"] == "introspect_schema"


def test_state_with_introspection_result() -> None:
    """Verify state can hold introspection result."""
    state = _create_initial_state()
    result = _minimal_introspection()
    state["introspection_result"] = result
    state["dialect"] = "sqlite"
    state["introspected_at"] = _now()
    
    assert state["introspection_result"] is not None
    assert state["introspection_result"].database_id == "db-001"
    assert state["dialect"] == "sqlite"


def test_state_with_snapshot_and_document_ids() -> None:
    """Verify state can track snapshot and document creation."""
    state = _create_initial_state()
    state["snapshot_id"] = "snap-abc123"
    state["document_ids"] = ["doc-001", "doc-002", "doc-003"]
    state["embedding_ids"] = ["emb-001", "emb-002", "emb-003"]
    
    assert state["snapshot_id"] == "snap-abc123"
    assert len(state["document_ids"]) == 3
    assert len(state["embedding_ids"]) == 3


def test_state_with_normalized_schema() -> None:
    """Verify state can hold normalized schema output."""
    state = _create_initial_state()
    schema = DatabaseSchema(
        database_id="db-001",
        dialect="sqlite",
        snapshot_id="snap-001",
        created_at=_now(),
    )

    state["normalized_schema"] = schema

    assert state["normalized_schema"] is not None
    assert state["normalized_schema"].snapshot_id == "snap-001"


# ---------------------------------------------------------------------------
# Status and control flow tests
# ---------------------------------------------------------------------------


def test_state_status_transitions() -> None:
    """Verify state supports expected status transitions."""
    state = _create_initial_state()
    
    # Simulate workflow transitions
    statuses = ["pending", "introspecting", "normalizing", "persisting", "indexing", "done"]
    for status in statuses:
        state["status"] = status
        state["current_node"] = f"{status}_node"
        assert state["status"] == status


def test_state_retry_count_increment() -> None:
    """Verify retry count can be incremented."""
    state = _create_initial_state()
    assert state["retry_count"] == 0
    
    for i in range(1, 4):
        state["retry_count"] = i
        assert state["retry_count"] == i


# ---------------------------------------------------------------------------
# Error and warning accumulation tests
# ---------------------------------------------------------------------------


def test_state_error_accumulation() -> None:
    """Verify errors can be accumulated (simulating add_messages behavior)."""
    state = _create_initial_state()
    
    # Simulate errors being appended
    state["errors"].append("Connection timeout")
    state["errors"].append("Query failed: syntax error")
    
    assert len(state["errors"]) == 2
    assert "Connection timeout" in state["errors"]


def test_state_warning_accumulation() -> None:
    """Verify warnings can be accumulated."""
    state = _create_initial_state()
    
    state["warnings"].append("Assuming default schema: public")
    state["warnings"].append("Row count estimate unavailable")
    
    assert len(state["warnings"]) == 2


# ---------------------------------------------------------------------------
# Refresh mode and parameters tests
# ---------------------------------------------------------------------------


def test_state_refresh_modes() -> None:
    """Verify state supports different refresh modes."""
    for refresh_mode in ["full", "incremental", "metadata_only"]:
        state = _create_initial_state()
        state["refresh_mode"] = refresh_mode
        assert state["refresh_mode"] == refresh_mode


def test_state_target_tables_filtering() -> None:
    """Verify target_tables filtering parameter."""
    state = _create_initial_state()
    
    # All tables (default)
    assert state["target_tables"] is None
    
    # Specific tables
    state["target_tables"] = ["orders", "customers"]
    assert state["target_tables"] == ["orders", "customers"]
    
    # Empty list (no tables)
    state["target_tables"] = []
    assert state["target_tables"] == []


def test_state_force_refresh_flag() -> None:
    """Verify force_refresh control flag."""
    state = _create_initial_state()
    assert state["force_refresh"] is False
    
    state["force_refresh"] = True
    assert state["force_refresh"] is True


# ---------------------------------------------------------------------------
# Connection config reference tests
# ---------------------------------------------------------------------------


def test_state_connection_config_ref() -> None:
    """Verify connection_config_ref holds a reference, not actual secrets."""
    state = _create_initial_state()
    assert state["connection_config_ref"] == "env:DATABASE_URL"
    
    # Reference to config key, not actual credentials
    state["connection_config_ref"] = "config:prod.primary_db"
    assert "password" not in state["connection_config_ref"]
    assert "secret" not in state["connection_config_ref"]


# ---------------------------------------------------------------------------
# Timestamp tracking tests
# ---------------------------------------------------------------------------


def test_state_timestamp_tracking() -> None:
    """Verify timestamps are tracked correctly."""
    state = _create_initial_state()
    now = _now()
    
    state["introspected_at"] = now
    state["completed_at"] = now
    
    assert state["introspected_at"] == now
    assert state["completed_at"] == now


def test_state_none_timestamps_before_execution() -> None:
    """Verify timestamps start as None."""
    state = _create_initial_state()
    assert state["introspected_at"] is None
    assert state["completed_at"] is None


# ---------------------------------------------------------------------------
# Workflow simulation tests
# ---------------------------------------------------------------------------


def test_full_workflow_state_transitions() -> None:
    """Simulate a complete successful workflow state evolution."""
    state = _create_initial_state()
    now = _now()
    
    # 1. Initial state
    assert state["status"] == "pending"
    assert state["introspection_result"] is None
    
    # 2. Introspection
    state["status"] = "introspecting"
    state["current_node"] = "introspect_schema"
    state["introspected_at"] = now
    state["introspection_result"] = _minimal_introspection()
    state["dialect"] = "sqlite"
    assert state["status"] == "introspecting"
    
    # 3. Normalization
    state["status"] = "normalizing"
    state["current_node"] = "normalize_schema"
    
    # 4. Persistence
    state["status"] = "persisting"
    state["current_node"] = "persist_schema_snapshot"
    state["snapshot_id"] = "snap-final"
    
    # 5. Indexing
    state["status"] = "indexing"
    state["current_node"] = "index_schema_embeddings"
    state["document_ids"] = ["doc-1", "doc-2"]
    state["embedding_ids"] = ["emb-1", "emb-2"]
    
    # 6. Complete
    state["status"] = "done"
    state["current_node"] = None
    state["completed_at"] = now
    
    assert state["status"] == "done"
    assert state["snapshot_id"] == "snap-final"
    assert len(state["document_ids"]) == 2


def test_workflow_with_errors() -> None:
    """Simulate a workflow that encounters errors."""
    state = _create_initial_state()
    now = _now()
    
    # Start introspection
    state["status"] = "introspecting"
    state["introspected_at"] = now
    
    # Error occurs
    state["errors"].append("Failed to connect to database: refused")
    state["status"] = "failed"
    state["retry_count"] = 1
    state["completed_at"] = now
    
    assert state["status"] == "failed"
    assert len(state["errors"]) == 1
    assert state["retry_count"] == 1
