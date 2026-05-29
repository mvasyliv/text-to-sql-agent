"""Tests for auth_callbacks: authenticate_with_password and build_auth_service_from_env."""
import asyncio
from pathlib import Path
import pytest
from text_to_sql_agent.config.settings import ConversationAuthSettings
from text_to_sql_agent.models.auth import UserLogin, UserRegistration
from text_to_sql_agent.repositories.sqlite_auth_repository import SQLiteAuthRepository
from text_to_sql_agent.services.auth_service import AuthService
from text_to_sql_agent.ui.auth_callbacks import authenticate_with_password, build_auth_service_from_env
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _settings(tmp_path: Path, auto_register: bool = True) -> ConversationAuthSettings:
    return ConversationAuthSettings(
        conversation_db_path=str(tmp_path / "auth.db"),
        auth_auto_register_on_first_login=auto_register,
        auth_min_password_length=4,
    )
def _service(tmp_path: Path, auto_register: bool = True) -> AuthService:
    s = _settings(tmp_path, auto_register)
    return AuthService(
        auth_repo=SQLiteAuthRepository(s.conversation_db_path),
        settings=s,
    )
def run(coro):
    """Run a coroutine synchronously for simple test cases."""
    return asyncio.run(coro)
# ---------------------------------------------------------------------------
# authenticate_with_password
# ---------------------------------------------------------------------------
class TestAuthenticateWithPassword:
    def test_returns_principal_for_valid_first_login(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        principal = run(authenticate_with_password("alice", "pass1234", svc))
        assert principal is not None
        assert principal.username == "alice"
    def test_returns_none_for_wrong_password(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        svc.register(UserRegistration(username="alice", password="correct1"))
        principal = run(authenticate_with_password("alice", "wrong", svc))
        assert principal is None
    def test_returns_none_for_unknown_user_when_auto_register_off(self, tmp_path: Path) -> None:
        svc = _service(tmp_path, auto_register=False)
        principal = run(authenticate_with_password("ghost", "any", svc))
        assert principal is None
    def test_returns_none_for_inactive_account(self, tmp_path: Path) -> None:
        repo = SQLiteAuthRepository(tmp_path / "auth.db")
        s = _settings(tmp_path)
        svc = AuthService(auth_repo=repo, settings=s)
        svc.register(UserRegistration(username="alice", password="pass1234"))
        account = repo.get_by_username("alice")
        repo.set_active(account.user_id, is_active=False)
        principal = run(authenticate_with_password("alice", "pass1234", svc))
        assert principal is None
    def test_second_login_returns_same_user_id(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        p1 = run(authenticate_with_password("alice", "pass1234", svc))
        p2 = run(authenticate_with_password("alice", "pass1234", svc))
        assert p1.user_id == p2.user_id
    def test_different_users_get_different_principals(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        pa = run(authenticate_with_password("alice", "pass1234", svc))
        pb = run(authenticate_with_password("bob", "pass5678", svc))
        assert pa.user_id != pb.user_id
        assert pa.username == "alice"
        assert pb.username == "bob"
# ---------------------------------------------------------------------------
# build_auth_service_from_env
# ---------------------------------------------------------------------------
class TestBuildAuthServiceFromEnv:
    def test_returns_auth_service(self, tmp_path: Path) -> None:
        settings = ConversationAuthSettings(
            conversation_db_path=str(tmp_path / "conversation.db"),
            auth_auto_register_on_first_login=True,
            auth_min_password_length=4,
        )
        svc = build_auth_service_from_env(settings=settings)
        assert isinstance(svc, AuthService)
    def test_auth_service_is_functional(self, tmp_path: Path) -> None:
        settings = ConversationAuthSettings(
            conversation_db_path=str(tmp_path / "conversation.db"),
            auth_auto_register_on_first_login=True,
            auth_min_password_length=4,
        )
        svc = build_auth_service_from_env(settings=settings)
        result = svc.register(UserRegistration(username="alice", password="test1234"))
        assert result.registered is True
