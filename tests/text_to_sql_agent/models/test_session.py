"""Tests for session identity models: User, Conversation, ChatMessage."""

from datetime import timezone

import pytest

from text_to_sql_agent.models.session import ChatMessage, Conversation, MessageRole, User


class TestUser:
    def test_required_fields(self):
        user = User(user_id="u-001", display_name="Alice")
        assert user.user_id == "u-001"
        assert user.display_name == "Alice"
        assert user.email is None
        assert user.is_active is True

    def test_created_at_is_utc(self):
        user = User(user_id="u-002", display_name="Bob")
        assert user.created_at.tzinfo == timezone.utc

    def test_optional_email(self):
        user = User(user_id="u-003", display_name="Carol", email="carol@example.com")
        assert user.email == "carol@example.com"

    def test_serialization_roundtrip(self):
        user = User(user_id="u-004", display_name="Dave", email="dave@example.com")
        assert User.model_validate(user.model_dump()) == user


class TestConversation:
    def test_required_fields(self):
        conv = Conversation(conversation_id="c-001", user_id="u-001")
        assert conv.conversation_id == "c-001"
        assert conv.user_id == "u-001"
        assert conv.title is None
        assert conv.is_active is True
        assert conv.metadata == {}

    def test_timestamps_are_utc(self):
        conv = Conversation(conversation_id="c-002", user_id="u-001")
        assert conv.created_at.tzinfo == timezone.utc
        assert conv.updated_at.tzinfo == timezone.utc

    def test_metadata_key_value(self):
        conv = Conversation(
            conversation_id="c-003",
            user_id="u-001",
            metadata={"db_id": "mydb", "dialect": "sqlite"},
        )
        assert conv.metadata["db_id"] == "mydb"

    def test_serialization_roundtrip(self):
        conv = Conversation(conversation_id="c-004", user_id="u-001", title="Test run")
        assert Conversation.model_validate(conv.model_dump()) == conv


class TestChatMessage:
    def test_user_message(self):
        msg = ChatMessage(
            message_id="m-001",
            conversation_id="c-001",
            role=MessageRole.USER,
            content="How many users are in the database?",
        )
        assert msg.role == MessageRole.USER
        assert msg.metadata == {}

    def test_assistant_message(self):
        msg = ChatMessage(
            message_id="m-002",
            conversation_id="c-001",
            role=MessageRole.ASSISTANT,
            content="There are 42 users.",
        )
        assert msg.role == MessageRole.ASSISTANT

    def test_tool_message_with_metadata(self):
        msg = ChatMessage(
            message_id="m-003",
            conversation_id="c-001",
            role=MessageRole.TOOL,
            content="SELECT COUNT(*) FROM users",
            metadata={"approval_status": "approved", "row_count": "1"},
        )
        assert msg.metadata["approval_status"] == "approved"

    def test_created_at_is_utc(self):
        msg = ChatMessage(
            message_id="m-004",
            conversation_id="c-001",
            role=MessageRole.USER,
            content="hello",
        )
        assert msg.created_at.tzinfo == timezone.utc

    def test_serialization_roundtrip(self):
        msg = ChatMessage(
            message_id="m-005",
            conversation_id="c-001",
            role=MessageRole.ASSISTANT,
            content="Done.",
        )
        assert ChatMessage.model_validate(msg.model_dump()) == msg

    @pytest.mark.parametrize("role", list(MessageRole))
    def test_all_roles_valid(self, role: MessageRole):
        msg = ChatMessage(
            message_id="m-x",
            conversation_id="c-001",
            role=role,
            content="test",
        )
        assert msg.role == role
