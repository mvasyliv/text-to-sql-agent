"""Tests for abstract SchemaIntrospectionProvider interface (T-2026-05-15-024)."""

from datetime import datetime, timezone
from typing import Any

import pytest

from text_to_sql_agent.models import RawIntrospectionResult, RawTableMeta
from text_to_sql_agent.repositories import SchemaIntrospectionProvider


# ---------------------------------------------------------------------------
# Test Implementation
# ---------------------------------------------------------------------------


class MockIntrospectionProvider(SchemaIntrospectionProvider):
    """Concrete mock implementation for testing the abstract interface."""

    def introspect(
        self,
        database_id: str,
        connection_config: dict[str, Any],
    ) -> RawIntrospectionResult:
        """Mock implementation that returns a predefined result."""
        # Simple mock: return empty schema
        return RawIntrospectionResult(
            database_id=database_id,
            dialect=connection_config.get("dialect", "unknown"),
            introspected_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
            tables=[],
        )


class StrictMockIntrospectionProvider(SchemaIntrospectionProvider):
    """Mock that validates connection config before introspection."""

    def introspect(
        self,
        database_id: str,
        connection_config: dict[str, Any],
    ) -> RawIntrospectionResult:
        """Validate config and return mock result."""
        if not connection_config.get("host"):
            raise ValueError("connection_config must include 'host'")
        
        table = RawTableMeta(
            name="test_table",
            table_type="TABLE",
            schema_name=connection_config.get("schema", "public"),
        )
        return RawIntrospectionResult(
            database_id=database_id,
            dialect=connection_config.get("dialect", "unknown"),
            introspected_at=datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc),
            tables=[table],
        )


# ---------------------------------------------------------------------------
# Abstract Base Class Tests
# ---------------------------------------------------------------------------


def test_schema_introspection_provider_cannot_instantiate_directly() -> None:
    """Verify that abstract base class cannot be instantiated directly."""
    with pytest.raises(TypeError) as exc_info:
        SchemaIntrospectionProvider()  # type: ignore[abstract]
    assert "abstract" in str(exc_info.value).lower()


def test_schema_introspection_provider_requires_introspect_implementation() -> None:
    """Verify that concrete subclass must implement introspect method."""
    # This class is intentionally incomplete
    class IncompleteProvider(SchemaIntrospectionProvider):
        pass
    
    with pytest.raises(TypeError):
        IncompleteProvider()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Concrete Implementation Tests
# ---------------------------------------------------------------------------


def test_mock_introspection_provider_instantiation() -> None:
    """Verify concrete implementation can be instantiated."""
    provider = MockIntrospectionProvider()
    assert provider is not None


def test_mock_introspection_provider_introspect_basic() -> None:
    """Test basic mock introspection call."""
    provider = MockIntrospectionProvider()
    result = provider.introspect(
        database_id="db-test",
        connection_config={"dialect": "sqlite"},
    )
    assert result.database_id == "db-test"
    assert result.dialect == "sqlite"
    assert result.tables == []


def test_mock_introspection_provider_with_empty_config() -> None:
    """Test that mock handles missing dialect gracefully."""
    provider = MockIntrospectionProvider()
    result = provider.introspect(
        database_id="db-x",
        connection_config={},
    )
    assert result.dialect == "unknown"


# ---------------------------------------------------------------------------
# Validation and Error Handling Tests
# ---------------------------------------------------------------------------


def test_strict_mock_provider_validates_host() -> None:
    """Verify that validation provider checks required config."""
    provider = StrictMockIntrospectionProvider()
    
    # Should fail without 'host'
    with pytest.raises(ValueError) as exc_info:
        provider.introspect(
            database_id="db-x",
            connection_config={},
        )
    assert "host" in str(exc_info.value).lower()


def test_strict_mock_provider_succeeds_with_valid_config() -> None:
    """Verify that validation provider works with valid config."""
    provider = StrictMockIntrospectionProvider()
    result = provider.introspect(
        database_id="db-prod",
        connection_config={
            "host": "localhost",
            "dialect": "postgresql",
            "schema": "public",
        },
    )
    assert result.database_id == "db-prod"
    assert result.dialect == "postgresql"
    assert len(result.tables) == 1
    assert result.tables[0].name == "test_table"


# ---------------------------------------------------------------------------
# Return Type Tests
# ---------------------------------------------------------------------------


def test_introspection_provider_returns_raw_introspection_result() -> None:
    """Verify that introspect method returns correct type."""
    provider = MockIntrospectionProvider()
    result = provider.introspect(
        database_id="db-type-check",
        connection_config={"dialect": "sqlite"},
    )
    assert isinstance(result, RawIntrospectionResult)


def test_introspection_result_has_required_fields() -> None:
    """Verify result has all required fields."""
    provider = MockIntrospectionProvider()
    result = provider.introspect(
        database_id="db-fields",
        connection_config={"dialect": "mysql"},
    )
    assert hasattr(result, "database_id")
    assert hasattr(result, "dialect")
    assert hasattr(result, "introspected_at")
    assert hasattr(result, "tables")
    assert hasattr(result, "warnings")


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


def test_multiple_provider_instances_are_independent() -> None:
    """Verify that multiple provider instances don't interfere."""
    provider1 = MockIntrospectionProvider()
    provider2 = StrictMockIntrospectionProvider()
    
    result1 = provider1.introspect(
        database_id="db-1",
        connection_config={"dialect": "sqlite"},
    )
    result2 = provider2.introspect(
        database_id="db-2",
        connection_config={"host": "server2", "dialect": "postgresql"},
    )
    
    assert result1.database_id == "db-1"
    assert result2.database_id == "db-2"
    assert len(result1.tables) == 0
    assert len(result2.tables) == 1


def test_provider_works_with_different_dialects() -> None:
    """Verify provider can handle different dialect configs."""
    provider = MockIntrospectionProvider()
    
    dialects = ["sqlite", "postgresql", "mysql", "mssql"]
    for dialect in dialects:
        result = provider.introspect(
            database_id=f"db-{dialect}",
            connection_config={"dialect": dialect},
        )
        assert result.dialect == dialect


def test_provider_preserves_database_id() -> None:
    """Verify provider correctly preserves database_id in result."""
    provider = MockIntrospectionProvider()
    db_ids = ["prod_warehouse", "staging_analytics", "test_local"]
    
    for db_id in db_ids:
        result = provider.introspect(
            database_id=db_id,
            connection_config={"dialect": "postgresql"},
        )
        assert result.database_id == db_id
