"""Tests for conversation history service ownership filtering and access checks."""

from datetime import datetime, timezone

import pytest

from text_to_sql_agent.models.session import ChatMessage, Conversation, MessageRole, User
from text_to_sql_agent.repositories.session_repository import InMemorySessionRepository
from text_to_sql_agent.services.conversation_history_service import (
    ConversationAccessError,
    ConversationHistoryService,
)


def _seed_repo() -> InMemorySessionRepository:
    repo = InMemorySessionRepository()
    repo.save_user(User(user_id="u-1", display_name="Alice"))
    repo.save_user(User(user_id="u-2", display_name="Bob"))

    repo.save_conversation(Conversation(conversation_id="c-1", user_id="u-1", title="Alice chat"))
    repo.save_conversation(Conversation(conversation_id="c-2", user_id="u-1", title="Alice second"))
    repo.save_conversation(Conversation(conversation_id="c-3", user_id="u-2", title="Bob chat"))

    repo.append_message(
        ChatMessage(
            message_id="m-1",
            conversation_id="c-1",
            role=MessageRole.USER,
            content="Hello",
        )
    )
    repo.append_message(
        ChatMessage(
            message_id="m-2",
            conversation_id="c-1",
            role=MessageRole.ASSISTANT,
            content="Hi",
        )
    )
    repo.append_message(
        ChatMessage(
            message_id="m-3",
            conversation_id="c-3",
            role=MessageRole.USER,
            content="Bob private",
        )
    )
    return repo


def test_list_user_conversations_returns_only_owned_conversations() -> None:
    repo = _seed_repo()
    service = ConversationHistoryService(repo)

    conversations = service.list_user_conversations("u-1")

    ids = {item.conversation_id for item in conversations}
    assert ids == {"c-1", "c-2"}


def test_load_user_conversation_returns_messages_for_owner() -> None:
    repo = _seed_repo()
    service = ConversationHistoryService(repo)

    record = service.load_user_conversation(user_id="u-1", conversation_id="c-1")

    assert record.conversation.conversation_id == "c-1"
    assert record.conversation.user_id == "u-1"
    assert [m.message_id for m in record.messages] == ["m-1", "m-2"]


def test_load_user_conversation_denies_access_to_other_user_data() -> None:
    repo = _seed_repo()
    service = ConversationHistoryService(repo)

    with pytest.raises(ConversationAccessError):
        service.load_user_conversation(user_id="u-1", conversation_id="c-3")


def test_load_user_conversation_raises_when_conversation_missing() -> None:
    repo = _seed_repo()
    service = ConversationHistoryService(repo)

    with pytest.raises(ConversationAccessError):
        service.load_user_conversation(user_id="u-1", conversation_id="does-not-exist")


def test_list_user_conversations_keeps_newest_first_order() -> None:
    repo = InMemorySessionRepository()
    now = datetime(2026, 5, 29, tzinfo=timezone.utc)
    repo.save_user(User(user_id="u-1", display_name="Alice"))
    repo.save_conversation(
        Conversation(
            conversation_id="c-old",
            user_id="u-1",
            title="Old",
            created_at=now,
            updated_at=now,
        )
    )
    repo.save_conversation(
        Conversation(
            conversation_id="c-new",
            user_id="u-1",
            title="New",
            created_at=now.replace(hour=23),
            updated_at=now.replace(hour=23),
        )
    )
    service = ConversationHistoryService(repo)

    conversations = service.list_user_conversations("u-1")

    assert [item.conversation_id for item in conversations] == ["c-new", "c-old"]


def test_load_user_conversation_returns_empty_messages_for_new_conversation() -> None:
    repo = InMemorySessionRepository()
    repo.save_user(User(user_id="u-1", display_name="Alice"))
    repo.save_conversation(Conversation(conversation_id="c-empty", user_id="u-1", title="Empty"))
    service = ConversationHistoryService(repo)

    record = service.load_user_conversation(user_id="u-1", conversation_id="c-empty")

    assert record.conversation.conversation_id == "c-empty"
    assert record.messages == []


