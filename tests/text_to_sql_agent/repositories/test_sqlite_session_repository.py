"""Tests for SQLiteSessionRepository: persistent conversation and message storage."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from text_to_sql_agent.models.session import ChatMessage, Conversation, MessageRole, User
from text_to_sql_agent.repositories.sqlite_session_repository import SQLiteSessionRepository
@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_conversation.db"
@pytest.fixture()
def repo(db_path: Path) -> SQLiteSessionRepository:
    return SQLiteSessionRepository(db_path)
def _user(user_id: str = "u-001", display_name: str = "Alice") -> User:
    return User(user_id=user_id, display_name=display_name)
def _conversation(conv_id: str, user_id: str, title: str | None = None) -> Conversation:
    return Conversation(conversation_id=conv_id, user_id=user_id, title=title)
def _message(msg_id: str, conv_id: str, content: str, role: MessageRole = MessageRole.USER) -> ChatMessage:
    return ChatMessage(message_id=msg_id, conversation_id=conv_id, role=role, content=content)
class TestUserPersistence:
    def test_save_and_get_user(self, repo: SQLiteSessionRepository) -> None:
        user = _user()
        repo.save_user(user)
        result = repo.get_user(user.user_id)
        assert result is not None
        assert result.user_id == user.user_id
        assert result.display_name == user.display_name
    def test_get_user_returns_none_when_missing(self, repo: SQLiteSessionRepository) -> None:
        assert repo.get_user("nonexistent") is None
    def test_save_user_is_idempotent(self, repo: SQLiteSessionRepository) -> None:
        user = _user()
        repo.save_user(user)
        repo.save_user(user)
        assert repo.get_user(user.user_id) is not None
    def test_save_user_does_not_overwrite_existing(self, repo: SQLiteSessionRepository) -> None:
        user = _user(display_name="Alice First")
        repo.save_user(user)
        # Second call with different display_name should be ignored (INSERT OR IGNORE)
        repo.save_user(_user(display_name="Alice Second"))
        result = repo.get_user(user.user_id)
        assert result.display_name == "Alice First"
class TestConversationPersistence:
    def test_save_and_get_conversation(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        conv = _conversation("c-001", "u-001", title="First chat")
        repo.save_conversation(conv)
        result = repo.get_conversation("c-001")
        assert result is not None
        assert result.conversation_id == "c-001"
        assert result.user_id == "u-001"
        assert result.title == "First chat"
    def test_get_conversation_returns_none_when_missing(self, repo: SQLiteSessionRepository) -> None:
        assert repo.get_conversation("nonexistent") is None
    def test_update_conversation_title(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        conv = _conversation("c-001", "u-001", title="Old title")
        repo.save_conversation(conv)
        updated = conv.model_copy(update={"title": "New title"})
        repo.save_conversation(updated)
        result = repo.get_conversation("c-001")
        assert result.title == "New title"
    def test_conversation_metadata_roundtrip(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        conv = Conversation(
            conversation_id="c-002",
            user_id="u-001",
            metadata={"db_id": "prod", "dialect": "sqlite"},
        )
        repo.save_conversation(conv)
        result = repo.get_conversation("c-002")
        assert result.metadata == {"db_id": "prod", "dialect": "sqlite"}

    def test_conversation_graph_thread_id_roundtrip(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        conv = Conversation(
            conversation_id="c-thread",
            user_id="u-001",
            graph_thread_id="thread-abc",
        )
        repo.save_conversation(conv)
        result = repo.get_conversation("c-thread")
        assert result is not None
        assert result.graph_thread_id == "thread-abc"

    def test_update_conversation_graph_thread_id(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        conv = Conversation(conversation_id="c-thread", user_id="u-001")
        repo.save_conversation(conv)
        repo.save_conversation(conv.model_copy(update={"graph_thread_id": "thread-new"}))
        result = repo.get_conversation("c-thread")
        assert result is not None
        assert result.graph_thread_id == "thread-new"
    def test_list_conversations_returns_only_user_conversations(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user("u-001"))
        repo.save_user(_user("u-002"))
        repo.save_conversation(_conversation("c-A", "u-001"))
        repo.save_conversation(_conversation("c-B", "u-001"))
        repo.save_conversation(_conversation("c-C", "u-002"))
        result = repo.list_conversations("u-001")
        ids = {c.conversation_id for c in result}
        assert ids == {"c-A", "c-B"}
    def test_list_conversations_newest_first(self, repo: SQLiteSessionRepository) -> None:
        now = datetime.now(timezone.utc)
        repo.save_user(_user())
        older = Conversation(
            conversation_id="c-old", user_id="u-001",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=2),
        )
        newer = Conversation(
            conversation_id="c-new", user_id="u-001",
            created_at=now,
            updated_at=now,
        )
        repo.save_conversation(older)
        repo.save_conversation(newer)
        result = repo.list_conversations("u-001")
        assert result[0].conversation_id == "c-new"
    def test_list_conversations_empty_for_unknown_user(self, repo: SQLiteSessionRepository) -> None:
        assert repo.list_conversations("nobody") == []
class TestMessagePersistence:
    def test_append_and_list_messages(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        repo.save_conversation(_conversation("c-001", "u-001"))
        repo.append_message(_message("m-1", "c-001", "Hello"))
        repo.append_message(_message("m-2", "c-001", "World"))
        result = repo.list_messages("c-001")
        assert len(result) == 2
        assert result[0].content == "Hello"
        assert result[1].content == "World"
    def test_messages_ordered_by_created_at(self, repo: SQLiteSessionRepository) -> None:
        now = datetime.now(timezone.utc)
        repo.save_user(_user())
        repo.save_conversation(_conversation("c-001", "u-001"))
        m1 = ChatMessage(message_id="m-1", conversation_id="c-001",
                         role=MessageRole.USER, content="first",
                         created_at=now - timedelta(seconds=10))
        m2 = ChatMessage(message_id="m-2", conversation_id="c-001",
                         role=MessageRole.ASSISTANT, content="second",
                         created_at=now)
        repo.append_message(m2)  # intentionally appended out of order
        repo.append_message(m1)
        result = repo.list_messages("c-001")
        assert result[0].content == "first"
        assert result[1].content == "second"
    def test_list_messages_empty_for_unknown_conversation(self, repo: SQLiteSessionRepository) -> None:
        assert repo.list_messages("nonexistent") == []
    def test_message_metadata_roundtrip(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        repo.save_conversation(_conversation("c-001", "u-001"))
        msg = ChatMessage(
            message_id="m-1", conversation_id="c-001",
            role=MessageRole.TOOL, content="done",
            metadata={"kind": "approval_result", "row_count": "5"},
        )
        repo.append_message(msg)
        result = repo.list_messages("c-001")
        assert result[0].metadata == {"kind": "approval_result", "row_count": "5"}
    def test_duplicate_message_id_is_silently_ignored(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        repo.save_conversation(_conversation("c-001", "u-001"))
        repo.append_message(_message("m-1", "c-001", "original"))
        repo.append_message(_message("m-1", "c-001", "duplicate"))
        result = repo.list_messages("c-001")
        assert len(result) == 1
        assert result[0].content == "original"
    def test_messages_are_isolated_per_conversation(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        repo.save_conversation(_conversation("c-A", "u-001"))
        repo.save_conversation(_conversation("c-B", "u-001"))
        repo.append_message(_message("m-1", "c-A", "in A"))
        repo.append_message(_message("m-2", "c-B", "in B"))
        assert len(repo.list_messages("c-A")) == 1
        assert len(repo.list_messages("c-B")) == 1
    def test_role_is_preserved(self, repo: SQLiteSessionRepository) -> None:
        repo.save_user(_user())
        repo.save_conversation(_conversation("c-001", "u-001"))
        repo.append_message(_message("m-1", "c-001", "hi", role=MessageRole.ASSISTANT))
        result = repo.list_messages("c-001")
        assert result[0].role == MessageRole.ASSISTANT
