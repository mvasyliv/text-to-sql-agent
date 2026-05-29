"""Integration-style UI tests for auth + conversation resume flow."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from text_to_sql_agent.models.auth import AuthPrincipal
from text_to_sql_agent.models.session import ChatMessage, Conversation, MessageRole
from text_to_sql_agent.repositories.session_repository import InMemorySessionRepository
from text_to_sql_agent.ui import chainlit_app
from text_to_sql_agent.ui.handlers import QueryTurnResult


class _SessionStore:
    _data: dict[str, object] = {}

    @classmethod
    def reset(cls) -> None:
        cls._data = {}

    @classmethod
    def get(cls, key: str):
        return cls._data.get(key)

    @classmethod
    def set(cls, key: str, value: object) -> None:
        cls._data[key] = value


class _UserStub:
    def __init__(
        self,
        *,
        identifier: str,
        display_name: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self.identifier = identifier
        self.display_name = display_name
        self.metadata = metadata or {}


def _make_chainlit_stub(sent_messages: list[str]):
    class MessageStub:
        def __init__(self, *, content: str, actions=None, elements=None) -> None:
            self.content = content
            self.actions = actions or []
            self.elements = elements or []

        async def send(self) -> None:
            sent_messages.append(self.content)

    class ChainlitStub:
        user_session = _SessionStore
        Message = MessageStub
        User = _UserStub

        @staticmethod
        def Action(*, name: str, payload: dict, label: str) -> dict[str, object]:
            return {"name": name, "payload": payload, "label": label}

    return ChainlitStub


def test_auth_open_conversation_and_continue_follow_up(monkeypatch):
    if not all(
        hasattr(chainlit_app, attr)
        for attr in ("password_auth_callback", "on_chat_start", "open_conversation", "on_message")
    ):
        pytest.skip("Chainlit callbacks are not available in this test environment.")

    sent_messages: list[str] = []
    start_calls: list[dict[str, str]] = []
    _SessionStore.reset()
    monkeypatch.setattr(chainlit_app, "cl", _make_chainlit_stub(sent_messages))

    async def _auth_stub(username: str, password: str, _service) -> AuthPrincipal | None:
        if username == "alice" and password == "pass1234":
            return AuthPrincipal(user_id="u-1", username="alice", display_name="Alice")
        return None

    monkeypatch.setattr(chainlit_app, "authenticate_with_password", _auth_stub)
    monkeypatch.setattr(chainlit_app, "_get_auth_service", lambda: object())
    monkeypatch.setattr(
        chainlit_app,
        "make_chainlit_user",
        lambda principal: _UserStub(
            identifier=principal.user_id,
            display_name=principal.display_name,
            metadata={"username": principal.username},
        ),
    )

    repository = InMemorySessionRepository()
    repository.save_conversation(
        Conversation(
            conversation_id="conv-old",
            user_id="u-1",
            title="Saved chat",
            graph_thread_id="thread-old",
            created_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 29, tzinfo=timezone.utc),
        )
    )
    repository.append_message(
        ChatMessage(
            message_id="m-1",
            conversation_id="conv-old",
            role=MessageRole.USER,
            content="How many users?",
        )
    )
    runtime = type("RuntimeStub", (), {"session_repository": repository})()
    monkeypatch.setattr(chainlit_app, "_get_runtime", lambda: runtime)

    def _start_stub(
        _runtime,
        *,
        user_id: str,
        conversation_id: str,
        user_question: str,
        selected_tables=None,
        thread_id=None,
    ) -> QueryTurnResult:
        del selected_tables, thread_id
        start_calls.append(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "user_question": user_question,
            }
        )
        return QueryTurnResult(
            thread_id="thread-followup",
            awaiting_approval=False,
            state={"execution_result": {"columns": [], "rows": [], "row_count": 0}},
        )

    async def _render_result_stub(_state: dict) -> None:
        sent_messages.append("result-rendered")

    monkeypatch.setattr(chainlit_app, "start_query_turn", _start_stub)
    monkeypatch.setattr(chainlit_app, "_render_query_result", _render_result_stub)

    session_user = asyncio.run(chainlit_app.password_auth_callback("alice", "pass1234"))
    assert session_user is not None
    _SessionStore.set("user", session_user)

    asyncio.run(chainlit_app.on_chat_start())

    open_action = type("ActionStub", (), {"payload": {"conversation_id": "conv-old"}})()
    asyncio.run(chainlit_app.open_conversation(open_action))

    message = type("MessageStub", (), {"content": "And only active users?"})()
    asyncio.run(chainlit_app.on_message(message))

    assert _SessionStore.get("user_id") == "u-1"
    assert _SessionStore.get("conversation_id") == "conv-old"
    assert start_calls[-1] == {
        "user_id": "u-1",
        "conversation_id": "conv-old",
        "user_question": "And only active users?",
    }
    assert any(item.startswith("Opened conversation:") for item in sent_messages)


def test_auth_open_conversation_denies_other_user_history(monkeypatch):
    if not all(
        hasattr(chainlit_app, attr)
        for attr in ("password_auth_callback", "on_chat_start", "open_conversation")
    ):
        pytest.skip("Chainlit callbacks are not available in this test environment.")

    sent_messages: list[str] = []
    _SessionStore.reset()
    monkeypatch.setattr(chainlit_app, "cl", _make_chainlit_stub(sent_messages))

    async def _auth_stub(username: str, password: str, _service) -> AuthPrincipal | None:
        if username == "alice" and password == "pass1234":
            return AuthPrincipal(user_id="u-1", username="alice", display_name="Alice")
        return None

    monkeypatch.setattr(chainlit_app, "authenticate_with_password", _auth_stub)
    monkeypatch.setattr(chainlit_app, "_get_auth_service", lambda: object())
    monkeypatch.setattr(
        chainlit_app,
        "make_chainlit_user",
        lambda principal: _UserStub(
            identifier=principal.user_id,
            display_name=principal.display_name,
            metadata={"username": principal.username},
        ),
    )

    repository = InMemorySessionRepository()
    repository.save_conversation(
        Conversation(
            conversation_id="conv-bob",
            user_id="u-2",
            title="Bob private",
            created_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 29, tzinfo=timezone.utc),
        )
    )
    runtime = type("RuntimeStub", (), {"session_repository": repository})()
    monkeypatch.setattr(chainlit_app, "_get_runtime", lambda: runtime)

    session_user = asyncio.run(chainlit_app.password_auth_callback("alice", "pass1234"))
    assert session_user is not None
    _SessionStore.set("user", session_user)

    asyncio.run(chainlit_app.on_chat_start())
    previous_conversation_id = str(_SessionStore.get("conversation_id"))

    action = type("ActionStub", (), {"payload": {"conversation_id": "conv-bob"}})()
    asyncio.run(chainlit_app.open_conversation(action))

    assert _SessionStore.get("conversation_id") == previous_conversation_id
    assert sent_messages[-1] == "Conversation not found for this user."

