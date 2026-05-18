"""Secret placeholder resolution utilities for environment configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

PLACEHOLDER_VALUE = "[LOAD_FROM_SECRETS]"


class SecretProvider(Protocol):
    """Protocol for key-based secret retrieval."""

    def get_secret(self, key: str) -> str | None:
        """Return secret value for key, or None if missing."""


class SecretResolutionError(ValueError):
    """Raised when required secret placeholders cannot be resolved."""


@dataclass(frozen=True, slots=True)
class SecretResolutionResult:
    """Resolved values and diagnostics after placeholder processing."""

    values: dict[str, str]
    unresolved_keys: list[str]
    warnings: list[str]


class FileSecretsProvider:
    """Read secrets from a local JSON file for development and test flows."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)
        self._cache: dict[str, str] | None = None

    def get_secret(self, key: str) -> str | None:
        data = self._load()
        return data.get(key)

    def _load(self) -> dict[str, str]:
        if self._cache is not None:
            return self._cache
        if not self._file_path.exists():
            self._cache = {}
            return self._cache

        raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise SecretResolutionError("Local secrets file must contain a JSON object.")

        normalized: dict[str, str] = {}
        for key, value in raw.items():
            if value is None:
                continue
            normalized[str(key)] = str(value)

        self._cache = normalized
        return self._cache


class AwsSecretsManagerProvider:
    """Load secrets from AWS Secrets Manager using a JSON secret payload."""

    def __init__(self, *, region: str, secret_name: str) -> None:
        self._region = region
        self._secret_name = secret_name
        self._cache: dict[str, str] | None = None

    def get_secret(self, key: str) -> str | None:
        data = self._load()
        return data.get(key)

    def _load(self) -> dict[str, str]:
        if self._cache is not None:
            return self._cache

        try:
            import boto3  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on runtime env
            raise SecretResolutionError(
                "boto3 is required for AwsSecretsManagerProvider."
            ) from exc

        client = boto3.client("secretsmanager", region_name=self._region)
        response = client.get_secret_value(SecretId=self._secret_name)
        payload = response.get("SecretString")
        if not payload:
            self._cache = {}
            return self._cache

        decoded = json.loads(payload)
        if not isinstance(decoded, dict):
            raise SecretResolutionError(
                "AWS secret payload must be a JSON object mapping keys to values."
            )

        normalized: dict[str, str] = {}
        for key, value in decoded.items():
            if value is None:
                continue
            normalized[str(key)] = str(value)

        self._cache = normalized
        return self._cache


def resolve_secret_placeholders(
    values: Mapping[str, str],
    *,
    environment: str,
    process_env: Mapping[str, str] | None = None,
    secret_provider: SecretProvider | None = None,
    placeholder_value: str = PLACEHOLDER_VALUE,
) -> SecretResolutionResult:
    """Resolve placeholder values using configured source priority.

    Source priority per key:
    1. process_env value when present and non-empty
    2. secret_provider value for placeholder entries
    3. original env-file value
    """
    resolved: dict[str, str] = {}
    unresolved_keys: list[str] = []
    warnings: list[str] = []
    env_values = process_env or {}

    for key, value in values.items():
        process_value = env_values.get(key)
        if process_value:
            resolved[key] = process_value
            continue

        if value != placeholder_value:
            resolved[key] = value
            continue

        secret_value = secret_provider.get_secret(key) if secret_provider else None
        if secret_value:
            resolved[key] = secret_value
            continue

        resolved[key] = value
        unresolved_keys.append(key)

    if unresolved_keys:
        message = (
            "Unresolved secret placeholders: " + ", ".join(sorted(unresolved_keys))
        )
        if environment.strip().lower() in {"prod", "production"}:
            raise SecretResolutionError(message)
        warnings.append(message)

    return SecretResolutionResult(
        values=resolved,
        unresolved_keys=unresolved_keys,
        warnings=warnings,
    )
