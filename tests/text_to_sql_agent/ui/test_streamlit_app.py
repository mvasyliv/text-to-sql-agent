"""Focused tests for Streamlit UI helper functions."""

from __future__ import annotations

from text_to_sql_agent.ui.streamlit_app import (
    _build_session_identity_diagnostics,
    _build_result_render_model,
    _build_sql_approval_markdown,
    _connection_config_from_env,
    _normalize_user_profile,
)


def test_connection_config_from_env_prefers_sqlite_path(monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", "/tmp/test.sqlite")
    monkeypatch.setenv("DB_PATH", "/tmp/fallback.sqlite")

    assert _connection_config_from_env() == {"path": "/tmp/test.sqlite"}


def test_connection_config_from_env_returns_none_without_env(monkeypatch) -> None:
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)

    assert _connection_config_from_env() is None


def test_build_result_render_model_for_success_payload() -> None:
    state = {
        "execution_result": {
            "row_count": 2,
            "columns": ["id", "name"],
            "rows": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
        },
        "insight_text": "Two rows found.",
    }

    result = _build_result_render_model(state)

    assert result["ok"] is True
    assert result["row_count"] == 2
    assert "| id | name |" in result["table_markdown"]
    assert result["insight"] == "Two rows found."


def test_build_sql_approval_markdown_includes_mode_and_sql() -> None:
    content = _build_sql_approval_markdown(
        {
            "generated_sql": "SELECT * FROM users;",
            "sql_generation_mode": "LLM",
        }
    )

    assert "Generation mode: **LLM**" in content
    assert "```sql" in content
    assert "SELECT * FROM users;" in content


def test_normalize_user_profile_applies_safe_fallbacks() -> None:
    assert _normalize_user_profile("", "") == ("streamlit-user", "streamlit-user")
    assert _normalize_user_profile("u-42", "") == ("u-42", "u-42")
    assert _normalize_user_profile(" u-42 ", " Alice ") == ("u-42", "Alice")


def test_build_session_identity_diagnostics_handles_missing_thread_id() -> None:
    content = _build_session_identity_diagnostics("conv-123", None)

    assert "conversation_id: `conv-123`" in content
    assert "pending_thread_id: `none`" in content


def test_build_session_identity_diagnostics_shows_pending_thread_id() -> None:
    content = _build_session_identity_diagnostics("conv-123", "thread-789")

    assert "pending_thread_id: `thread-789`" in content


