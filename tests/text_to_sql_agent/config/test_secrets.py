"""Tests for secret placeholder resolution utilities."""

from pathlib import Path

import pytest

from text_to_sql_agent.config.secrets import (
    FileSecretsProvider,
    PLACEHOLDER_VALUE,
    SecretResolutionError,
    resolve_secret_placeholders,
)


class _MappingSecretProvider:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    def get_secret(self, key: str) -> str | None:
        return self._mapping.get(key)


def test_resolver_uses_process_env_first() -> None:
    values = {
        "PG_PASSWORD": PLACEHOLDER_VALUE,
        "PG_USER": "app_user",
    }
    provider = _MappingSecretProvider({"PG_PASSWORD": "from-provider"})

    result = resolve_secret_placeholders(
        values,
        environment="prod",
        process_env={"PG_PASSWORD": "from-process-env"},
        secret_provider=provider,
    )

    assert result.values["PG_PASSWORD"] == "from-process-env"
    assert result.values["PG_USER"] == "app_user"
    assert result.unresolved_keys == []


def test_resolver_uses_secret_provider_for_placeholders() -> None:
    values = {
        "PG_PASSWORD": PLACEHOLDER_VALUE,
        "MYSQL_PASSWORD": PLACEHOLDER_VALUE,
    }
    provider = _MappingSecretProvider({"PG_PASSWORD": "pg-secret", "MYSQL_PASSWORD": "my-secret"})

    result = resolve_secret_placeholders(
        values,
        environment="production",
        secret_provider=provider,
    )

    assert result.values["PG_PASSWORD"] == "pg-secret"
    assert result.values["MYSQL_PASSWORD"] == "my-secret"
    assert result.unresolved_keys == []


def test_resolver_keeps_non_placeholder_values() -> None:
    values = {
        "DB_DRIVER": "sqlite",
        "SQLITE_PATH": "tests/text_to_sql_agent/db/test_database.db",
    }

    result = resolve_secret_placeholders(values, environment="dev")

    assert result.values == values
    assert result.unresolved_keys == []


def test_resolver_fails_fast_in_production_when_unresolved() -> None:
    values = {
        "PG_PASSWORD": PLACEHOLDER_VALUE,
        "VAULT_TOKEN": PLACEHOLDER_VALUE,
    }

    with pytest.raises(SecretResolutionError) as exc_info:
        resolve_secret_placeholders(values, environment="prod")

    message = str(exc_info.value)
    assert "PG_PASSWORD" in message
    assert "VAULT_TOKEN" in message


def test_resolver_warns_in_dev_for_unresolved() -> None:
    values = {"PG_PASSWORD": PLACEHOLDER_VALUE}

    result = resolve_secret_placeholders(values, environment="dev")

    assert result.values["PG_PASSWORD"] == PLACEHOLDER_VALUE
    assert result.unresolved_keys == ["PG_PASSWORD"]
    assert len(result.warnings) == 1


def test_file_secrets_provider_reads_json_file(tmp_path: Path) -> None:
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text(
        '{"PG_PASSWORD": "pg-from-file", "VAULT_TOKEN": "vault-from-file"}',
        encoding="utf-8",
    )

    provider = FileSecretsProvider(secrets_file)

    assert provider.get_secret("PG_PASSWORD") == "pg-from-file"
    assert provider.get_secret("VAULT_TOKEN") == "vault-from-file"
    assert provider.get_secret("MISSING") is None


def test_file_secrets_provider_missing_file_returns_empty(tmp_path: Path) -> None:
    provider = FileSecretsProvider(tmp_path / "absent.json")

    assert provider.get_secret("PG_PASSWORD") is None
