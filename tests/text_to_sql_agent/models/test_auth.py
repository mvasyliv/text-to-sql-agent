"""Tests for auth-facing Pydantic models: UserAccount, UserRegistration, UserLogin, AuthPrincipal."""

import pytest
from pydantic import ValidationError

from text_to_sql_agent.models.auth import AuthPrincipal, UserAccount, UserLogin, UserRegistration


class TestUserAccount:
    def test_required_fields(self) -> None:
        account = UserAccount(
            user_id="u-001",
            username="alice",
            password_hash="$argon2id$...",
            display_name="Alice",
        )
        assert account.user_id == "u-001"
        assert account.username == "alice"
        assert account.password_hash == "$argon2id$..."
        assert account.display_name == "Alice"
        assert account.is_active is True

    def test_timestamps_are_set_by_default(self) -> None:
        account = UserAccount(
            user_id="u-001",
            username="alice",
            password_hash="hash",
            display_name="Alice",
        )
        assert account.created_at is not None
        assert account.updated_at is not None

    def test_inactive_account(self) -> None:
        account = UserAccount(
            user_id="u-002",
            username="bob",
            password_hash="hash",
            display_name="Bob",
            is_active=False,
        )
        assert account.is_active is False

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            UserAccount(username="alice", password_hash="hash", display_name="Alice")  # type: ignore[call-arg]


class TestUserRegistration:
    def test_basic_registration(self) -> None:
        reg = UserRegistration(username="alice", password="secret123")
        assert reg.username == "alice"
        assert reg.password == "secret123"
        assert reg.display_name == ""

    def test_username_is_stripped(self) -> None:
        reg = UserRegistration(username="  alice  ", password="pass")
        assert reg.username == "alice"

    def test_display_name_stripped(self) -> None:
        reg = UserRegistration(username="alice", password="pass", display_name="  Alice  ")
        assert reg.display_name == "Alice"

    def test_resolved_display_name_falls_back_to_username(self) -> None:
        reg = UserRegistration(username="alice", password="pass")
        assert reg.resolved_display_name() == "alice"

    def test_resolved_display_name_uses_provided_name(self) -> None:
        reg = UserRegistration(username="alice", password="pass", display_name="Alice W.")
        assert reg.resolved_display_name() == "Alice W."

    def test_empty_username_raises(self) -> None:
        with pytest.raises(ValidationError):
            UserRegistration(username="", password="pass")

    def test_empty_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            UserRegistration(username="alice", password="")


class TestUserLogin:
    def test_basic_login(self) -> None:
        login = UserLogin(username="alice", password="secret")
        assert login.username == "alice"
        assert login.password == "secret"

    def test_username_is_stripped(self) -> None:
        login = UserLogin(username="  alice  ", password="secret")
        assert login.username == "alice"

    def test_missing_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            UserLogin(username="alice")  # type: ignore[call-arg]


class TestAuthPrincipal:
    def test_from_account(self) -> None:
        account = UserAccount(
            user_id="u-001",
            username="alice",
            password_hash="$hash$",
            display_name="Alice",
        )
        principal = AuthPrincipal.from_account(account)
        assert principal.user_id == "u-001"
        assert principal.username == "alice"
        assert principal.display_name == "Alice"
        assert principal.is_active is True
        assert not hasattr(principal, "password_hash")

    def test_inactive_account_preserves_flag(self) -> None:
        account = UserAccount(
            user_id="u-002",
            username="bob",
            password_hash="hash",
            display_name="Bob",
            is_active=False,
        )
        principal = AuthPrincipal.from_account(account)
        assert principal.is_active is False

    def test_direct_construction(self) -> None:
        principal = AuthPrincipal(user_id="u-003", username="carol", display_name="Carol")
        assert principal.user_id == "u-003"
        assert principal.is_active is True

