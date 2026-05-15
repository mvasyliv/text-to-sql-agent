"""Configuration tests for repository-backed settings."""

from pathlib import Path


def test_test_env_points_to_repository_sqlite_database() -> None:
    """The test environment should use the checked-in SQLite database file."""
    env_test_path = Path(".env.test")
    database_path = Path("tests/text_to_sql_agent/db/test_database.db")

    assert env_test_path.exists()
    assert database_path.exists()

    env_test_text = env_test_path.read_text(encoding="utf-8")
    assert "SQLITE_PATH=tests/text_to_sql_agent/db/test_database.db" in env_test_text
