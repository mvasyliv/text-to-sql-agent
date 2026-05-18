"""Tests for runtime settings loading with secret resolution."""

from pathlib import Path

import pytest

from text_to_sql_agent.config.settings import load_runtime_environment


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_load_runtime_environment_resolves_file_backend_for_dev(tmp_path: Path) -> None:
    _write(
        tmp_path / ".env",
        "ENVIRONMENT=dev\nSECRETS_BACKEND=file\nSECRETS_LOCAL_FILE=.secrets.local.json\nPG_USER=app\n",
    )
    _write(tmp_path / ".env.dev", "PG_PASSWORD=[LOAD_FROM_SECRETS]\n")
    _write(tmp_path / ".secrets.local.json", '{"PG_PASSWORD": "dev-secret"}')

    process_env: dict[str, str] = {}
    result = load_runtime_environment(project_root=tmp_path, process_env=process_env)

    assert result.values["PG_PASSWORD"] == "dev-secret"
    assert process_env["PG_PASSWORD"] == "dev-secret"
    assert process_env["PG_USER"] == "app"
    assert process_env["ENVIRONMENT"] == "dev"


def test_process_env_overrides_file_and_secret_values(tmp_path: Path) -> None:
    _write(
        tmp_path / ".env",
        "ENVIRONMENT=dev\nSECRETS_BACKEND=file\nSECRETS_LOCAL_FILE=.secrets.local.json\n",
    )
    _write(tmp_path / ".env.dev", "PG_PASSWORD=[LOAD_FROM_SECRETS]\n")
    _write(tmp_path / ".secrets.local.json", '{"PG_PASSWORD": "secret-from-file"}')

    process_env: dict[str, str] = {"PG_PASSWORD": "from-process"}
    result = load_runtime_environment(project_root=tmp_path, process_env=process_env)

    assert result.values["PG_PASSWORD"] == "from-process"
    assert process_env["PG_PASSWORD"] == "from-process"


def test_prod_raises_on_unresolved_placeholder(tmp_path: Path) -> None:
    _write(tmp_path / ".env", "ENVIRONMENT=prod\nSECRETS_BACKEND=file\n")
    _write(tmp_path / ".env.prod", "PG_PASSWORD=[LOAD_FROM_SECRETS]\n")

    with pytest.raises(ValueError):
        load_runtime_environment(project_root=tmp_path, process_env={})


def test_loads_env_specific_file_by_environment(tmp_path: Path) -> None:
    _write(tmp_path / ".env", "ENVIRONMENT=test\nSECRETS_BACKEND=none\n")
    _write(tmp_path / ".env.test", "SQLITE_PATH=tests/text_to_sql_agent/db/test_database.db\n")

    process_env: dict[str, str] = {}
    result = load_runtime_environment(project_root=tmp_path, process_env=process_env)

    assert result.values["SQLITE_PATH"] == "tests/text_to_sql_agent/db/test_database.db"
    assert process_env["SQLITE_PATH"] == "tests/text_to_sql_agent/db/test_database.db"
    assert process_env["ENVIRONMENT"] == "test"
