"""Tests for InMemorySessionRepository: user, conversation, and message persistence."""

import pytest

from text_to_sql_agent.models.session import ChatMessage, Conversation, MessageRole, User
from text_to_sql_agent.repositories.session_repository import InMemorySessionRepository


@pytest.fixture()
def repo() -> InMemorySessionRepository:
    return InMemorySessionRepository()


@pytest.fixture()
def user() -> User:
    return User(user_id="u-001", display_name="Alice")


@pytest.fixture()
def conversation(user: User) -> Conversation:
    return Conversation(conversation_id="c-001", user_id=user.user_id)


def _msg(message_id: str, conversation_id: str, content: str) -> ChatMessage:
    return ChatMessage(
        message_id=message_id,
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=content,
    )


class TestUserPersistence:
    def test_save_and_retrieve(self, repo: InMemorySessionRepository, user: User):
        repo.save_user(user)
        assert repo.get_user(user.user_id) == user

    def test_missing_user_returns_none(self, repo: InMemorySessionRepository):
        assert repo.get_user("nonexistent") is None

    def test_overwrite_user(self, repo: InMemorySessionRepository, user: User):
        repo.save_user(user)
        updated = user.model_copy(update={"display_name": "Alicia"})
        repo.save_user(updated)
        assert repo.get_user(user.user_id).display_name == "Alicia"


class TestConversationPersistence:
    def test_save_and_retrieve(
        self,
        repo: InMemorySessionRepository,
        conversation: Conversation,
    ):
        repo.save_conversation(conversation)
        assert repo.get_conversation(conversation.conversation_id) == conversation

    def test_missing_conversation_returns_none(self, repo: InMemorySessionRepository):
        assert repo.get_conversation("nonexistent") is None

    def test_list_conversations_for_user(
        self,
        repo: InMemorySessionRepository,
        user: User,
    ):
        c1 = Conversation(conversation_id="c-001", user_id=user.user_id)
        c2 = Conversation(conversation_id="c-002", user_id=user.user_id)
        other = Conversation(conversation_id="c-003", user_id="u-other")
        for c in (c1, c2, other):
            repo.save_conversation(c)
        result = repo.list_conversations(user.user_id)
        assert len(result) == 2
        ids = {c.conversation_id for c in result}
        assert ids == {"c-001", "c-002"}

    def test_list_conversations_newest_first(
        self,
        repo: InMemorySessionRepository,
        user: User,
    ):
        from datetime import datetime, timedelta, timezone

        base = datetime.now(timezone.utc)
        older = Conversation(
            conversation_id="c-old",
            user_id=user.user_id,
            created_at=base - timedelta(hours=1),
            updated_at=base - timedelta(hours=1),
        )
        newer = Conversation(
            conversation_id="c-new",
            user_id=user.user_id,
            created_at=base,
            updated_at=base,
        )
        repo.save_conversation(older)
        repo.save_conversation(newer)
        result = repo.list_conversations(user.user_id)
        assert result[0].conversation_id == "c-new"


class TestMessagePersistence:
    def test_append_and_list(
        self,
        repo: InMemorySessionRepository,
        conversation: Conversation,
    ):
        repo.save_conversation(conversation)
        m1 = _msg("m-001", conversation.conversation_id, "first")
        m2 = _msg("m-002", conversation.conversation_id, "second")
        repo.append_message(m1)
        repo.append_message(m2)
        result = repo.list_messages(conversation.conversation_id)
        assert len(result) == 2
        assert result[0].content == "first"
        assert result[1].content == "second"

    def test_list_messages_empty_conversation(
        self,
        repo: InMemorySessionRepository,
        conversation: Conversation,
    ):
        repo.save_conversation(conversation)
        assert repo.list_messages(conversation.conversation_id) == []

    def test_list_messages_unknown_conversation(self, repo: InMemorySessionRepository):
        assert repo.list_messages("nonexistent") == []

    def test_messages_are_isolated_per_conversation(
        self,
        repo: InMemorySessionRepository,
    ):
        c1 = Conversation(conversation_id="c-A", user_id="u-001")
        c2 = Conversation(conversation_id="c-B", user_id="u-001")
        repo.save_conversation(c1)
        repo.save_conversation(c2)
        repo.append_message(_msg("m-1", "c-A", "in c-A"))
        repo.append_message(_msg("m-2", "c-B", "in c-B"))
        assert len(repo.list_messages("c-A")) == 1
        assert len(repo.list_messages("c-B")) == 1
