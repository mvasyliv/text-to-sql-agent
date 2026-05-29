"""Tests for AuthService: password hashing, verify, register-or-login policy."""
from pathlib import Path
import pytest
from text_to_sql_agent.config.settings import ConversationAuthSettings
from text_to_sql_agent.models.auth import UserLogin, UserRegistration
from text_to_sql_agent.repositories.sqlite_auth_repository import SQLiteAuthRepository
from text_to_sql_agent.services.auth_service import (
    AuthError,
    AuthService,
    hash_password,
    verify_password,
)
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _settings(auto_register: bool = True, min_password_length: int = 4) -> ConversationAuthSettings:
    return ConversationAuthSettings(
        auth_auto_register_on_first_login=auto_register,
        auth_min_password_length=min_password_length,
    )
def _repo(tmp_path: Path) -> SQLiteAuthRepository:
    return SQLiteAuthRepository(tmp_path / "auth_test.db")
def _service(tmp_path: Path, **kwargs) -> AuthService:
    return AuthService(auth_repo=_repo(tmp_path), settings=_settings(**kwargs))
# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------
class TestPasswordHelpers:
    def test_hash_is_not_plain_text(self) -> None:
        h = hash_password("mysecret")
        assert h != "mysecret"
        assert h.startswith("$argon2")
    def test_verify_correct_password(self) -> None:
        h = hash_password("mysecret")
        assert verify_password("mysecret", h) is True
    def test_verify_wrong_password(self) -> None:
        h = hash_password("mysecret")
        assert verify_password("wrong", h) is False
    def test_two_hashes_of_same_password_differ(self) -> None:
        h1 = hash_password("abc1234")
        h2 = hash_password("abc1234")
        assert h1 != h2  # Argon2 uses random salt
# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
class TestRegister:
    def test_register_creates_account(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        result = svc.register(UserRegistration(username="alice", password="password1"))
        assert result.registered is True
        assert result.principal.username == "alice"
    def test_register_display_name_falls_back_to_username(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        result = svc.register(UserRegistration(username="alice", password="password1"))
        assert result.principal.display_name == "alice"
    def test_register_uses_provided_display_name(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        result = svc.register(
            UserRegistration(username="alice", password="password1", display_name="Alice W.")
        )
        assert result.principal.display_name == "Alice W."
    def test_register_duplicate_username_raises(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        svc.register(UserRegistration(username="alice", password="password1"))
        with pytest.raises(AuthError, match="already taken"):
            svc.register(UserRegistration(username="alice", password="other123"))
    def test_register_password_too_short_raises(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, min_password_length=8)
        with pytest.raises(AuthError, match="at least 8 characters"):
            svc.register(UserRegistration(username="alice", password="short"))
    def test_register_password_at_minimum_length_succeeds(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, min_password_length=6)
        result = svc.register(UserRegistration(username="alice", password="123456"))
        assert result.registered is True
# ---------------------------------------------------------------------------
# Authenticate or register — auto-register ON
# ---------------------------------------------------------------------------
class TestAuthenticateOrRegisterAutoOn:
    def test_first_login_creates_account(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, auto_register=True)
        result = svc.authenticate_or_register(UserLogin(username="alice", password="password1"))
        assert result.registered is True
        assert result.principal.username == "alice"
    def test_second_login_authenticates_existing(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, auto_register=True)
        svc.authenticate_or_register(UserLogin(username="alice", password="password1"))
        result = svc.authenticate_or_register(UserLogin(username="alice", password="password1"))
        assert result.registered is False
        assert result.principal.username == "alice"
    def test_wrong_password_on_existing_account_raises(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, auto_register=True)
        svc.authenticate_or_register(UserLogin(username="alice", password="password1"))
        with pytest.raises(AuthError, match="Invalid password"):
            svc.authenticate_or_register(UserLogin(username="alice", password="wrongpass"))
    def test_inactive_account_raises(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        svc = AuthService(auth_repo=repo, settings=_settings(auto_register=True))
        svc.authenticate_or_register(UserLogin(username="alice", password="password1"))
        account = repo.get_by_username("alice")
        repo.set_active(account.user_id, is_active=False)
        with pytest.raises(AuthError, match="disabled"):
            svc.authenticate_or_register(UserLogin(username="alice", password="password1"))
    def test_auto_register_short_password_raises(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, auto_register=True, min_password_length=8)
        with pytest.raises(AuthError, match="at least 8 characters"):
            svc.authenticate_or_register(UserLogin(username="alice", password="hi"))
# ---------------------------------------------------------------------------
# Authenticate or register — auto-register OFF
# ---------------------------------------------------------------------------
class TestAuthenticateOrRegisterAutoOff:
    def test_unknown_user_raises_when_auto_register_disabled(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, auto_register=False)
        with pytest.raises(AuthError, match="Unknown username"):
            svc.authenticate_or_register(UserLogin(username="ghost", password="any"))
    def test_existing_user_authenticates_when_auto_register_disabled(self, tmp_path: Path) -> None:
        # Pre-register via explicit register()
        svc = _service(tmp_path, auto_register=False)
        svc.register(UserRegistration(username="alice", password="password1"))
        result = svc.authenticate_or_register(UserLogin(username="alice", password="password1"))
        assert result.registered is False
        assert result.principal.username == "alice"
# ---------------------------------------------------------------------------
# Isolation: multiple users
# ---------------------------------------------------------------------------
class TestMultiUserIsolation:
    def test_two_users_get_different_principals(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, auto_register=True)
        r1 = svc.authenticate_or_register(UserLogin(username="alice", password="pass1111"))
        r2 = svc.authenticate_or_register(UserLogin(username="bob", password="pass2222"))
        assert r1.principal.user_id != r2.principal.user_id
        assert r1.principal.username == "alice"
        assert r2.principal.username == "bob"
    def test_alice_password_does_not_unlock_bob(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, auto_register=True)
        svc.authenticate_or_register(UserLogin(username="alice", password="alicepass"))
        svc.authenticate_or_register(UserLogin(username="bob", password="bobpass"))
        with pytest.raises(AuthError):
            svc.authenticate_or_register(UserLogin(username="bob", password="alicepass"))
