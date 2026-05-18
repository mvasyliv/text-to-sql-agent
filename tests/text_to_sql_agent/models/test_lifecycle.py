"""Tests for lifecycle and operational Pydantic models (T-2026-05-15-022)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from text_to_sql_agent.models.lifecycle import (
    SchemaRefreshRequest,
    SchemaSnapshotRef,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# SchemaSnapshotRef
# ---------------------------------------------------------------------------


def test_schema_snapshot_ref_required_fields() -> None:
    ref = SchemaSnapshotRef(
        snapshot_id="snap-001",
        database_id="db-001",
        dialect="sqlite",
        created_at=_now(),
        table_count=42,
        status="fresh",
    )
    assert ref.snapshot_id == "snap-001"
    assert ref.database_id == "db-001"
    assert ref.dialect == "sqlite"
    assert ref.table_count == 42
    assert ref.status == "fresh"


def test_schema_snapshot_ref_status_values() -> None:
    valid_statuses = ["fresh", "stale", "indexing", "indexed", "failed"]
    for status in valid_statuses:
        ref = SchemaSnapshotRef(
            snapshot_id="snap-x",
            database_id="db-x",
            dialect="postgresql",
            created_at=_now(),
            table_count=10,
            status=status,
        )
        assert ref.status == status


def test_schema_snapshot_ref_missing_required_raises() -> None:
    with pytest.raises(ValidationError):
        SchemaSnapshotRef(
            snapshot_id="snap-x",
            database_id="db-x",
            dialect="mysql",
            created_at=_now(),
            # Missing required: table_count, status
        )  # type: ignore[call-arg]


def test_schema_snapshot_ref_zero_table_count() -> None:
    """Edge case: empty database with no tables."""
    ref = SchemaSnapshotRef(
        snapshot_id="snap-empty",
        database_id="db-empty",
        dialect="postgresql",
        created_at=_now(),
        table_count=0,
        status="fresh",
    )
    assert ref.table_count == 0


def test_schema_snapshot_ref_large_table_count() -> None:
    """Edge case: large database with many tables."""
    ref = SchemaSnapshotRef(
        snapshot_id="snap-large",
        database_id="db-large",
        dialect="mssql",
        created_at=_now(),
        table_count=10000,
        status="indexed",
    )
    assert ref.table_count == 10000


def test_schema_snapshot_ref_serialization_roundtrip() -> None:
    ref = SchemaSnapshotRef(
        snapshot_id="snap-003",
        database_id="db-003",
        dialect="mysql",
        created_at=_now(),
        table_count=25,
        status="indexing",
    )
    dumped = ref.model_dump()
    restored = SchemaSnapshotRef.model_validate(dumped)
    assert restored.snapshot_id == "snap-003"
    assert restored.status == "indexing"
    assert restored.table_count == 25


# ---------------------------------------------------------------------------
# SchemaRefreshRequest
# ---------------------------------------------------------------------------


def test_schema_refresh_request_minimal() -> None:
    """Minimal request: only database_id is required."""
    req = SchemaRefreshRequest(database_id="db-001")
    assert req.database_id == "db-001"
    assert req.refresh_mode == "full"
    assert req.target_tables is None
    assert req.force is False


def test_schema_refresh_request_full_spec() -> None:
    """Full request with all fields specified."""
    req = SchemaRefreshRequest(
        database_id="db-002",
        refresh_mode="incremental",
        target_tables=["orders", "customers"],
        force=True,
    )
    assert req.refresh_mode == "incremental"
    assert req.target_tables == ["orders", "customers"]
    assert req.force is True


def test_schema_refresh_request_refresh_modes() -> None:
    """Test all valid refresh_mode values."""
    for mode in ["full", "incremental", "metadata_only"]:
        req = SchemaRefreshRequest(database_id="db-x", refresh_mode=mode)
        assert req.refresh_mode == mode


def test_schema_refresh_request_target_tables_empty_list() -> None:
    """Edge case: explicitly empty target tables list."""
    req = SchemaRefreshRequest(
        database_id="db-003",
        target_tables=[],
    )
    assert req.target_tables == []


def test_schema_refresh_request_target_tables_many() -> None:
    """Edge case: many target tables."""
    tables = [f"table_{i}" for i in range(100)]
    req = SchemaRefreshRequest(
        database_id="db-004",
        target_tables=tables,
    )
    assert len(req.target_tables) == 100


def test_schema_refresh_request_force_false_explicit() -> None:
    """Verify that force=False is the default."""
    req1 = SchemaRefreshRequest(database_id="db-x")
    req2 = SchemaRefreshRequest(database_id="db-x", force=False)
    assert req1.force is False
    assert req2.force is False


def test_schema_refresh_request_missing_required_raises() -> None:
    with pytest.raises(ValidationError):
        SchemaRefreshRequest()  # type: ignore[call-arg]


def test_schema_refresh_request_serialization_roundtrip() -> None:
    req = SchemaRefreshRequest(
        database_id="db-005",
        refresh_mode="metadata_only",
        target_tables=["products", "inventory"],
        force=True,
    )
    dumped = req.model_dump()
    restored = SchemaRefreshRequest.model_validate(dumped)
    assert restored.database_id == "db-005"
    assert restored.refresh_mode == "metadata_only"
    assert restored.target_tables == ["products", "inventory"]
    assert restored.force is True


def test_schema_refresh_request_none_target_tables_vs_empty_list() -> None:
    """Distinguish between None (all tables) and empty list (no tables)."""
    req_all = SchemaRefreshRequest(database_id="db-x", target_tables=None)
    req_none = SchemaRefreshRequest(database_id="db-x")
    req_empty = SchemaRefreshRequest(database_id="db-x", target_tables=[])
    
    assert req_all.target_tables is None
    assert req_none.target_tables is None
    assert req_empty.target_tables == []
    assert req_empty.target_tables != req_all.target_tables


# ---------------------------------------------------------------------------
# Integration: Request + Response workflow
# ---------------------------------------------------------------------------


def test_refresh_request_snapshot_ref_pair() -> None:
    """Verify that a RefreshRequest and SnapshotRef can be paired in workflow."""
    req = SchemaRefreshRequest(
        database_id="db-workflow",
        refresh_mode="full",
        force=False,
    )
    
    ref = SchemaSnapshotRef(
        snapshot_id="snap-workflow-001",
        database_id=req.database_id,  # Link back to request
        dialect="postgresql",
        created_at=_now(),
        table_count=15,
        status="indexed",
    )
    
    # Verify consistency
    assert ref.database_id == req.database_id
    assert ref.status == "indexed"  # Successfully completed after refresh


def test_multiple_refresh_requests_for_single_db() -> None:
    """Verify that multiple refresh requests can target the same database."""
    db_id = "db-multi"
    req1 = SchemaRefreshRequest(database_id=db_id, refresh_mode="full")
    req2 = SchemaRefreshRequest(database_id=db_id, refresh_mode="incremental")
    req3 = SchemaRefreshRequest(database_id=db_id, refresh_mode="metadata_only", force=True)
    
    assert req1.database_id == req2.database_id == req3.database_id
    assert req1.refresh_mode != req2.refresh_mode != req3.refresh_mode
