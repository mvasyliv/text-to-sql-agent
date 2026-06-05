"""Tests for MCP runtime settings loading."""

from text_to_sql_agent.config.settings import load_mcp_runtime_settings


def test_load_mcp_runtime_settings_uses_defaults() -> None:
    settings = load_mcp_runtime_settings(env={})

    assert settings.sqlite.endpoint is None
    assert settings.sqlite.transport == "stdio"
    assert settings.sqlite.credentials_source == "none"
    assert settings.sqlite.timeout_ms == 30000

    assert settings.postgresql.endpoint is None
    assert settings.postgresql.transport == "stdio"
    assert settings.postgresql.credentials_source == "env"
    assert settings.postgresql.timeout_ms == 30000

    assert settings.athena.endpoint is None
    assert settings.athena.transport == "stdio"
    assert settings.athena.credentials_source == "aws"
    assert settings.athena.timeout_ms == 120000


def test_load_mcp_runtime_settings_reads_env_values() -> None:
    settings = load_mcp_runtime_settings(
        env={
            "MCP_SQLITE_ENDPOINT": "sqlite-mcp --db tests/text_to_sql_agent/db/test_database.db",
            "MCP_SQLITE_TRANSPORT": "stdio",
            "MCP_SQLITE_CREDENTIALS_SOURCE": "file",
            "MCP_SQLITE_TIMEOUT_MS": "15000",
            "MCP_POSTGRESQL_ENDPOINT": "http://localhost:3101/mcp",
            "MCP_POSTGRESQL_TRANSPORT": "http",
            "MCP_POSTGRESQL_CREDENTIALS_SOURCE": "env",
            "MCP_POSTGRESQL_TIMEOUT_MS": "45000",
            "MCP_ATHENA_ENDPOINT": "https://mcp-athena.internal",
            "MCP_ATHENA_TRANSPORT": "sse",
            "MCP_ATHENA_CREDENTIALS_SOURCE": "aws",
            "MCP_ATHENA_TIMEOUT_MS": "180000",
        }
    )

    assert settings.sqlite.endpoint == "sqlite-mcp --db tests/text_to_sql_agent/db/test_database.db"
    assert settings.sqlite.credentials_source == "file"
    assert settings.sqlite.timeout_ms == 15000

    assert settings.postgresql.endpoint == "http://localhost:3101/mcp"
    assert settings.postgresql.transport == "http"
    assert settings.postgresql.timeout_ms == 45000

    assert settings.athena.endpoint == "https://mcp-athena.internal"
    assert settings.athena.transport == "sse"
    assert settings.athena.timeout_ms == 180000


def test_load_mcp_runtime_settings_normalizes_invalid_values_and_aliases() -> None:
    settings = load_mcp_runtime_settings(
        env={
            "MCP_SQLITE_ENDPOINT": "   ",
            "MCP_SQLITE_TRANSPORT": "invalid",
            "MCP_SQLITE_CREDENTIALS_SOURCE": "invalid",
            "MCP_SQLITE_TIMEOUT_MS": "0",
            "MCP_PG_ENDPOINT": "http://localhost:3201/mcp",
            "MCP_PG_TRANSPORT": "http",
            "MCP_PG_CREDENTIALS_SOURCE": "env",
            "MCP_PG_TIMEOUT_MS": "-5",
            "MCP_ATHENA_TIMEOUT_MS": "not-a-number",
        }
    )

    assert settings.sqlite.endpoint is None
    assert settings.sqlite.transport == "stdio"
    assert settings.sqlite.credentials_source == "none"
    assert settings.sqlite.timeout_ms == 1

    assert settings.postgresql.endpoint == "http://localhost:3201/mcp"
    assert settings.postgresql.transport == "http"
    assert settings.postgresql.credentials_source == "env"
    assert settings.postgresql.timeout_ms == 1

    assert settings.athena.timeout_ms == 120000