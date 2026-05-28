"""Tests for conversation DB and auth policy settings loading."""

from text_to_sql_agent.config.settings import load_conversation_auth_settings


def test_load_conversation_auth_settings_uses_defaults() -> None:
    settings = load_conversation_auth_settings(env={})

    assert settings.conversation_db_path == "conversation.db"
    assert settings.auth_auto_register_on_first_login is True
    assert settings.auth_min_password_length == 8


def test_load_conversation_auth_settings_reads_env_values() -> None:
    settings = load_conversation_auth_settings(
        env={
            "CONVERSATION_DB_PATH": "data/conversation.sqlite3",
            "AUTH_AUTO_REGISTER_ON_FIRST_LOGIN": "false",
            "AUTH_MIN_PASSWORD_LENGTH": "12",
        }
    )

    assert settings.conversation_db_path == "data/conversation.sqlite3"
    assert settings.auth_auto_register_on_first_login is False
    assert settings.auth_min_password_length == 12


def test_load_conversation_auth_settings_normalizes_invalid_values() -> None:
    settings = load_conversation_auth_settings(
        env={
            "CONVERSATION_DB": "conversation-alt.db",
            "AUTH_AUTO_REGISTER_ON_FIRST_LOGIN": "not-a-bool",
            "AUTH_MIN_PASSWORD_LENGTH": "2",
        }
    )

    assert settings.conversation_db_path == "conversation-alt.db"
    assert settings.auth_auto_register_on_first_login is True
    assert settings.auth_min_password_length == 4

