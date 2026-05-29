"""Tests for SQLiteAuthRepository: user creation, lookup, and update operations."""
from datetime import datetime, timezone
from pathlib import Path
import pytest
from text_to_sql_agent.models.auth import UserAccount
from text_to_sql_agent.repositories.sqlite_auth_repository import SQLiteAuthRepository
@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_auth.db"
@pytest.fixture()
def repo(db_path: Path) -> SQLiteAuthRepository:
    return SQLiteAuthRepository(db_path)
def _account(
    user_id: str = "u-001",
    username: str = "alice",
    password_hash: str = "$argon2id$hash",
    display_name: str = "Alice",
    is_active: bool = True,
) -> UserAccount:
    return UserAccount(
        user_id=user_id,
        username=username,
        password_hash=password_hash,
        display_name=display_name,
        is_active=is_active,
    )
class TestCreateAccount:
    def test_create_and_retrieve_by_username(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account())
        result = repo.get_by_username("alice")
        assert result is not None
        assert result.user_id == "u-001"
        assert result.username == "alice"
        assert result.password_hash == "$argon2id$hash"
        assert result.display_name == "Alice"
        assert result.is_active is True
    def test_create_and_retrieve_by_user_id(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account())
        result = repo.get_by_user_id("u-001")
        assert result is not None
        assert result.username == "alice"
    def test_duplicate_username_raises_value_error(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account())
        with pytest.raises(ValueError, match="already exists"):
            repo.create_account(_account(user_id="u-002"))
    def test_duplicate_user_id_raises_value_error(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account())
        with pytest.raises(ValueError, match="already exists"):
            repo.create_account(_account(username="bob"))
    def test_timestamps_are_stored_and_retrieved(self, repo: SQLiteAuthRepository) -> None:
        now = datetime.now(timezone.utc)
        account = UserAccount(
            user_id="u-001",
            username="alice",
            password_hash="hash",
            display_name="Alice",
            created_at=now,
            updated_at=now,
        )
        repo.create_account(account)
        result = repo.get_by_user_id("u-001")
        assert abs((result.created_at - now).total_seconds()) < 1
    def test_inactive_account_is_persisted(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account(is_active=False))
        result = repo.get_by_username("alice")
        assert result.is_active is False
class TestGetLookups:
    def test_get_by_username_returns_none_when_missing(self, repo: SQLiteAuthRepository) -> None:
        assert repo.get_by_username("nobody") is None
    def test_get_by_user_id_returns_none_when_missing(self, repo: SQLiteAuthRepository) -> None:
        assert repo.get_by_user_id("nonexistent") is None
    def test_username_exists_true(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account())
        assert repo.username_exists("alice") is True
    def test_username_exists_false(self, repo: SQLiteAuthRepository) -> None:
        assert repo.username_exists("ghost") is False
    def test_multiple_accounts_isolated(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account("u-001", "alice"))
        repo.create_account(_account("u-002", "bob", display_name="Bob"))
        alice = repo.get_by_username("alice")
        bob = repo.get_by_username("bob")
        assert alice.user_id == "u-001"
        assert bob.user_id == "u-002"
class TestUpdatePasswordHash:
    def test_update_password_hash(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account())
        repo.update_password_hash("u-001", "$argon2id$newhash")
        result = repo.get_by_user_id("u-001")
        assert result.password_hash == "$argon2id$newhash"
    def test_update_password_hash_updates_updated_at(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account())
        original = repo.get_by_user_id("u-001")
        repo.update_password_hash("u-001", "$argon2id$newhash")
        updated = repo.get_by_user_id("u-001")
        assert updated.updated_at >= original.updated_at
    def test_update_password_hash_unknown_user_raises(self, repo: SQLiteAuthRepository) -> None:
        with pytest.raises(ValueError, match="No account found"):
            repo.update_password_hash("nonexistent", "hash")
class TestSetActive:
    def test_deactivate_account(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account())
        repo.set_active("u-001", is_active=False)
        result = repo.get_by_user_id("u-001")
        assert result.is_active is False
    def test_reactivate_account(self, repo: SQLiteAuthRepository) -> None:
        repo.create_account(_account(is_active=False))
        repo.set_active("u-001", is_active=True)
        result = repo.get_by_user_id("u-001")
        assert result.is_active is True
    def test_set_active_unknown_user_raises(self, repo: SQLiteAuthRepository) -> None:
        with pytest.raises(ValueError, match="No account found"):
            repo.set_active("nonexistent", is_active=False)
