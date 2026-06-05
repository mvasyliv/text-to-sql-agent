"""Tests for the Athena MCP client repository."""

from text_to_sql_agent.models import MCPExecuteRequest, MCPHealthRequest, MCPSchemaRequest, MCPToolRequestMeta
from text_to_sql_agent.repositories import AthenaMCPClientRepository


def _meta() -> MCPToolRequestMeta:
    return MCPToolRequestMeta(request_id="req-001", user_id="u-001", conversation_id="c-001")


def _build_repository(invoker):
    return AthenaMCPClientRepository(
        endpoint="mcp://athena-adapter",
        catalog="AwsDataCatalog",
        database="analytics",
        workgroup="primary",
        invoker=invoker,
    )


def test_athena_mcp_execute_read_only_returns_success_payload() -> None:
    def invoker(_tool_name, _payload, _timeout_ms):
        return {
            "columns": ["id", "name"],
            "rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "elapsed_ms": 27,
        }

    repository = _build_repository(invoker)
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="athena",
            database_id="db-main",
            sql="SELECT id, name FROM users",
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert response.result.columns == ["id", "name"]
    assert response.result.row_count == 2
    assert response.result.rows[0]["name"] == "Alice"


def test_athena_mcp_execute_read_only_applies_row_limit() -> None:
    def invoker(_tool_name, _payload, _timeout_ms):
        return {
            "rows": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Carol"},
            ],
            "elapsed_ms": 42,
        }

    repository = _build_repository(invoker)
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="athena",
            database_id="db-main",
            sql="SELECT id, name FROM users",
            row_limit=2,
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert response.result.row_count == 2
    assert response.result.truncated is True


def test_athena_mcp_execute_read_only_rejects_non_read_only_sql() -> None:
    repository = _build_repository(lambda *_: {})
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="athena",
            database_id="db-main",
            sql="DELETE FROM users",
            meta=_meta(),
        )
    )

    assert response.status == "error"
    assert response.error.code == "forbidden_operation"


def test_athena_mcp_fetch_schema_returns_tables() -> None:
    def invoker(_tool_name, _payload, _timeout_ms):
        return {
            "tables": [
                {
                    "name": "users",
                    "schema_name": "analytics",
                    "table_type": "TABLE",
                    "columns": [
                        {"name": "id", "data_type": "bigint", "nullable": False},
                        {"name": "name", "data_type": "varchar", "nullable": True},
                    ],
                },
                {
                    "name": "v_users",
                    "schema_name": "analytics",
                    "table_type": "VIEW",
                    "columns": [{"name": "name", "data_type": "varchar", "nullable": True}],
                },
            ]
        }

    repository = _build_repository(invoker)
    response = repository.fetch_schema(
        MCPSchemaRequest(
            dialect="athena",
            database_id="db-main",
            include_views=True,
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert len(response.result.tables) == 2
    assert response.result.tables[0].name == "users"
    assert response.result.tables[0].columns[0].nullable is False
    assert response.result.tables[1].table_type == "VIEW"


def test_athena_mcp_check_health_returns_success() -> None:
    def invoker(_tool_name, _payload, _timeout_ms):
        return {"reachable": True, "latency_ms": 19, "server_version": "Athena engine 3"}

    repository = _build_repository(invoker)
    response = repository.check_health(
        MCPHealthRequest(
            dialect="athena",
            database_id="db-main",
            meta=_meta(),
        )
    )

    assert response.status == "success"
    assert response.result.reachable is True
    assert response.result.server_version == "Athena engine 3"


def test_athena_mcp_returns_unsupported_dialect_error() -> None:
    repository = _build_repository(lambda *_: {})
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="sqlite",
            database_id="db-main",
            sql="SELECT 1",
            meta=_meta(),
        )
    )

    assert response.status == "error"
    assert response.error.code == "unsupported_dialect"


def test_athena_mcp_maps_transport_errors() -> None:
    def invoker(_tool_name, _payload, _timeout_ms):
        raise RuntimeError("remote mcp transport failed")

    repository = _build_repository(invoker)
    response = repository.execute_read_only(
        MCPExecuteRequest(
            dialect="athena",
            database_id="db-main",
            sql="SELECT 1",
            meta=_meta(),
        )
    )

    assert response.status == "error"
    assert response.error.code == "transport_error"
    assert response.error.retriable is True
