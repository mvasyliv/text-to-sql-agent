"""Runtime settings loader with secret placeholder resolution."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, MutableMapping

from dotenv import dotenv_values

from text_to_sql_agent.config.secrets import (
    AwsSecretsManagerProvider,
    FileSecretsProvider,
    SecretResolutionResult,
    resolve_secret_placeholders,
)


def load_runtime_environment(
    *,
    project_root: str | Path | None = None,
    environment: str | None = None,
    process_env: MutableMapping[str, str] | None = None,
) -> SecretResolutionResult:
    """Load env files, resolve secret placeholders, and populate process env.

    Source priority per key:
    1. Existing process environment value
    2. Secret backend value for placeholder entries
    3. Value from merged env files
    """
    resolved_process_env = process_env if process_env is not None else os.environ
    root_path = Path(project_root or Path.cwd())

    resolved_environment = (
        environment
        or resolved_process_env.get("ENVIRONMENT")
        or _infer_environment_from_env_file(root_path)
        or "dev"
    ).strip().lower()

    file_values = _load_environment_values(root_path, resolved_environment)
    backend = (
        resolved_process_env.get("SECRETS_BACKEND")
        or file_values.get("SECRETS_BACKEND")
        or "none"
    ).strip().lower()

    provider = _build_secret_provider(
        backend,
        process_env=resolved_process_env,
        file_values=file_values,
        root_path=root_path,
    )

    result = resolve_secret_placeholders(
        file_values,
        environment=resolved_environment,
        process_env=resolved_process_env,
        secret_provider=provider,
    )

    for key, value in result.values.items():
        resolved_process_env.setdefault(key, value)

    resolved_process_env.setdefault("ENVIRONMENT", resolved_environment)
    return result


def _load_environment_values(root_path: Path, environment: str) -> dict[str, str]:
    values: dict[str, str] = {}

    base_file = root_path / ".env"
    values.update(_read_env_file(base_file))

    env_file = root_path / _environment_file_name(environment)
    if env_file != base_file:
        values.update(_read_env_file(env_file))

    return values


def _environment_file_name(environment: str) -> str:
    if environment == "prod" or environment == "production":
        return ".env.prod"
    if environment == "test":
        return ".env.test"
    return ".env.dev"


def _read_env_file(file_path: Path) -> dict[str, str]:
    if not file_path.exists():
        return {}

    raw = dotenv_values(file_path)
    values: dict[str, str] = {}
    for key, value in raw.items():
        if value is None:
            continue
        values[str(key)] = str(value)
    return values


def _infer_environment_from_env_file(root_path: Path) -> str | None:
    base_file = root_path / ".env"
    if not base_file.exists():
        return None
    values = _read_env_file(base_file)
    env_value = values.get("ENVIRONMENT")
    return env_value.strip().lower() if env_value else None


def _build_secret_provider(
    backend: str,
    *,
    process_env: Mapping[str, str],
    file_values: Mapping[str, str],
    root_path: Path,
):
    if backend == "none" or backend == "":
        return None

    if backend == "file":
        local_file = (
            process_env.get("SECRETS_LOCAL_FILE")
            or file_values.get("SECRETS_LOCAL_FILE")
            or ".secrets.local.json"
        )
        return FileSecretsProvider(root_path / local_file)

    if backend == "aws_secrets_manager":
        region = process_env.get("SECRETS_AWS_REGION") or file_values.get("SECRETS_AWS_REGION")
        secret_name = process_env.get("SECRETS_AWS_SECRET_NAME") or file_values.get("SECRETS_AWS_SECRET_NAME")
        if not region or not secret_name:
            return None
        return AwsSecretsManagerProvider(region=region, secret_name=secret_name)

    return None
