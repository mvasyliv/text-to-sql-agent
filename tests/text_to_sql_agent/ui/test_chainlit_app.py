"""Tests for Chainlit app helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from text_to_sql_agent.models.session import ChatMessage, Conversation, MessageRole
from text_to_sql_agent.repositories.session_repository import InMemorySessionRepository
from text_to_sql_agent.ui import chainlit_app
from text_to_sql_agent.ui.handlers import QueryTurnResult


def test_build_chart_elements_returns_empty_without_figure():
    assert chainlit_app._build_chart_elements(None) == []


def test_build_chart_elements_skips_when_plotly_missing(monkeypatch):
    class PlotlyStub:
        def __init__(self, **_: object) -> None:
            raise ModuleNotFoundError("No module named 'plotly'")

    class ChainlitStub:
        Plotly = PlotlyStub

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)

    assert chainlit_app._build_chart_elements({"data": [], "layout": {}}) == []


def test_render_query_result_sends_export_message_before_chart(monkeypatch):
    sent_messages: list[dict[str, object]] = []

    class MessageStub:
        def __init__(
            self,
            *,
            content: str,
            actions: list[dict[str, str]] | None = None,
            elements: list[object] | None = None,
        ) -> None:
            self.content = content
            self.actions = actions or []
            self.elements = elements or []

        async def send(self) -> None:
            sent_messages.append(
                {
                    "content": self.content,
                    "actions": self.actions,
                    "elements": self.elements,
                }
            )

    class ChainlitStub:
        Message = MessageStub

        @staticmethod
        def Action(*, name: str, payload: dict, label: str) -> dict[str, str]:
            return {"name": name, "label": label}

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)
    monkeypatch.setattr(chainlit_app, "_build_chart_elements", lambda _: ["chart"])

    asyncio.run(
        chainlit_app._render_query_result(
            {
                "execution_result": {
                    "columns": ["id"],
                    "rows": [{"id": 1}],
                    "row_count": 1,
                },
                "insight_text": "One row returned.",
                "chart_spec": {"type": "bar", "x": ["1"], "y": [1]},
            }
        )
    )

    assert [message["content"] for message in sent_messages] == [
        "Rows returned: 1",
        "| id |\n| --- |\n| 1 |",
        "Insight: One row returned.\n\n**Export results:**",
        "One-shot chart",
    ]
    assert sent_messages[2]["actions"] == [
        {"name": "export_csv", "label": "Export CSV"},
        {"name": "export_json", "label": "Export JSON"},
    ]


def test_render_sql_approval_shows_llm_notice(monkeypatch):
    sent_messages: list[str] = []

    class MessageStub:
        def __init__(self, *, content: str, actions=None, elements=None) -> None:
            self.content = content

        async def send(self) -> None:
            sent_messages.append(self.content)

    class ChainlitStub:
        Message = MessageStub

        @staticmethod
        def Action(*, name: str, payload: dict, label: str) -> dict[str, str]:
            return {"name": name, "label": label}

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)

    turn = QueryTurnResult(
        thread_id="t-1",
        awaiting_approval=True,
        state={
            "generated_sql": "SELECT 1",
            "llm_user_notice": "LLM is unavailable right now.",
            "sql_generation_mode": "Few-shot fallback",
        },
    )

    asyncio.run(chainlit_app._render_sql_approval(turn))
    assert len(sent_messages) == 1
    assert "LLM is unavailable right now." in sent_messages[0]
    assert "Proposed SQL query:" in sent_messages[0]
    assert "Generation mode: **Few-shot fallback**" in sent_messages[0]


def test_resolve_authenticated_identity_from_session_user(monkeypatch):
    class SessionStub:
        @staticmethod
        def get(key: str):
            if key == "user":
                return type(
                    "UserStub",
                    (),
                    {
                        "identifier": "u-123",
                        "display_name": "Alice",
                        "metadata": {"username": "alice"},
                    },
                )()
            return None

    class ChainlitStub:
        user_session = SessionStub()

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)
    assert chainlit_app._resolve_authenticated_identity() == ("u-123", "alice", "Alice")


def test_resolve_authenticated_identity_uses_safe_defaults(monkeypatch):
    class SessionStub:
        @staticmethod
        def get(key: str):
            return None

    class ChainlitStub:
        user_session = SessionStub()

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)
    assert chainlit_app._resolve_authenticated_identity() == (
        "anonymous",
        "anonymous",
        "Anonymous",
    )


def test_build_history_actions_builds_open_action_payloads(monkeypatch):
    class ChainlitStub:
        @staticmethod
        def Action(*, name: str, payload: dict, label: str) -> dict[str, object]:
            return {"name": name, "payload": payload, "label": label}

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)
    conversations = [
        Conversation(
            conversation_id="conv-001",
            user_id="u-1",
            title="First conversation",
            created_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
        ),
        Conversation(
            conversation_id="conv-002",
            user_id="u-1",
            title="Second conversation",
            created_at=datetime(2026, 5, 29, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 29, tzinfo=timezone.utc),
        ),
    ]

    actions = chainlit_app._build_history_actions(conversations)
    assert actions == [
        {
            "name": "open_conversation",
            "payload": {"conversation_id": "conv-001"},
            "label": "First conversation",
        },
        {
            "name": "open_conversation",
            "payload": {"conversation_id": "conv-002"},
            "label": "Second conversation",
        },
    ]


def test_build_new_conversation_action(monkeypatch):
    class ChainlitStub:
        @staticmethod
        def Action(*, name: str, payload: dict, label: str) -> dict[str, object]:
            return {"name": name, "payload": payload, "label": label}

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)
    assert chainlit_app._build_new_conversation_action() == {
        "name": "new_conversation",
        "payload": {},
        "label": "Start new conversation",
    }


def test_render_user_conversation_list_sends_actions(monkeypatch):
    sent_messages: list[dict[str, object]] = []

    class MessageStub:
        def __init__(self, *, content: str, actions=None, elements=None) -> None:
            self.content = content
            self.actions = actions or []

        async def send(self) -> None:
            sent_messages.append({"content": self.content, "actions": self.actions})

    class ChainlitStub:
        Message = MessageStub

        @staticmethod
        def Action(*, name: str, payload: dict, label: str) -> dict[str, object]:
            return {"name": name, "payload": payload, "label": label}

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)

    repository = InMemorySessionRepository()
    repository.save_conversation(
        Conversation(
            conversation_id="conv-101",
            user_id="u-1",
            title="Monthly sales",
            created_at=datetime(2026, 5, 27, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 27, tzinfo=timezone.utc),
        )
    )
    repository.save_conversation(
        Conversation(
            conversation_id="conv-102",
            user_id="u-1",
            title="Top products",
            created_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
        )
    )

    runtime = type("RuntimeStub", (), {"session_repository": repository})()
    asyncio.run(chainlit_app._render_user_conversation_list(runtime, user_id="u-1"))

    assert len(sent_messages) == 1
    assert sent_messages[0]["content"] == "Recent conversations (2). Select one to open or start a new one."
    assert sent_messages[0]["actions"] == [
        {
            "name": "new_conversation",
            "payload": {},
            "label": "Start new conversation",
        },
        {
            "name": "open_conversation",
            "payload": {"conversation_id": "conv-102"},
            "label": "Top products",
        },
        {
            "name": "open_conversation",
            "payload": {"conversation_id": "conv-101"},
            "label": "Monthly sales",
        },
    ]


def test_render_user_conversation_list_handles_empty_history(monkeypatch):
    sent_messages: list[dict[str, object]] = []

    class MessageStub:
        def __init__(self, *, content: str, actions=None, elements=None) -> None:
            self.content = content
            self.actions = actions or []

        async def send(self) -> None:
            sent_messages.append({"content": self.content, "actions": self.actions})

    class ChainlitStub:
        Message = MessageStub

        @staticmethod
        def Action(*, name: str, payload: dict, label: str) -> dict[str, object]:
            return {"name": name, "payload": payload, "label": label}

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)

    runtime = type("RuntimeStub", (), {"session_repository": InMemorySessionRepository()})()
    asyncio.run(chainlit_app._render_user_conversation_list(runtime, user_id="u-empty"))
    assert sent_messages == [
        {
            "content": "No previous conversations yet. Start a new conversation.",
            "actions": [
                {
                    "name": "new_conversation",
                    "payload": {},
                    "label": "Start new conversation",
                }
            ],
        }
    ]


def test_open_conversation_loads_messages_and_switches_active_conversation(monkeypatch):
    if not hasattr(chainlit_app, "open_conversation"):
        pytest.skip("Chainlit is not installed in this test environment.")

    sent_messages: list[str] = []

    class SessionStub:
        _data = {"user_id": "u-1"}

        @classmethod
        def get(cls, key: str):
            return cls._data.get(key)

        @classmethod
        def set(cls, key: str, value: object) -> None:
            cls._data[key] = value

    class MessageStub:
        def __init__(self, *, content: str, actions=None, elements=None) -> None:
            self.content = content

        async def send(self) -> None:
            sent_messages.append(self.content)

    class ChainlitStub:
        user_session = SessionStub
        Message = MessageStub

        @staticmethod
        def Action(*, name: str, payload: dict, label: str) -> dict[str, object]:
            return {"name": name, "payload": payload, "label": label}

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)

    repo = InMemorySessionRepository()
    repo.save_conversation(
        Conversation(
            conversation_id="conv-open-1",
            user_id="u-1",
            title="Saved chat",
            graph_thread_id="thread-abc",
            created_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 29, tzinfo=timezone.utc),
        )
    )
    repo.append_message(
        ChatMessage(
            message_id="m-1",
            conversation_id="conv-open-1",
            role=MessageRole.USER,
            content="How many users?",
        )
    )
    repo.append_message(
        ChatMessage(
            message_id="m-2",
            conversation_id="conv-open-1",
            role=MessageRole.ASSISTANT,
            content="SELECT COUNT(*) FROM users;",
        )
    )
    runtime = type("RuntimeStub", (), {"session_repository": repo})()
    monkeypatch.setattr(chainlit_app, "_get_runtime", lambda: runtime)

    action = type("ActionStub", (), {"payload": {"conversation_id": "conv-open-1"}})()
    asyncio.run(chainlit_app.open_conversation(action))

    assert SessionStub.get("conversation_id") == "conv-open-1"
    assert SessionStub.get("pending_thread_id") is None
    assert SessionStub.get("awaiting_edit_sql") is False
    assert SessionStub.get("last_state") is None
    assert sent_messages[0] == "Opened conversation: Saved chat."
    assert "**User:** How many users?" in sent_messages[1]
    assert "**Assistant:** SELECT COUNT(*) FROM users;" in sent_messages[1]


def test_new_conversation_sets_new_id_and_keeps_history_accessible(monkeypatch):
    if not hasattr(chainlit_app, "new_conversation"):
        pytest.skip("Chainlit is not installed in this test environment.")

    sent_messages: list[str] = []
    rendered_lists: list[str] = []

    class SessionStub:
        _data = {"user_id": "u-1", "conversation_id": "conv-old"}

        @classmethod
        def get(cls, key: str):
            return cls._data.get(key)

        @classmethod
        def set(cls, key: str, value: object) -> None:
            cls._data[key] = value

    class MessageStub:
        def __init__(self, *, content: str, actions=None, elements=None) -> None:
            self.content = content

        async def send(self) -> None:
            sent_messages.append(self.content)

    class ChainlitStub:
        user_session = SessionStub
        Message = MessageStub

        @staticmethod
        def Action(*, name: str, payload: dict, label: str) -> dict[str, object]:
            return {"name": name, "payload": payload, "label": label}

    monkeypatch.setattr(chainlit_app, "cl", ChainlitStub)
    runtime = type("RuntimeStub", (), {"session_repository": InMemorySessionRepository()})()
    monkeypatch.setattr(chainlit_app, "_get_runtime", lambda: runtime)

    async def _render_stub(runtime_obj, *, user_id: str) -> None:
        assert runtime_obj is runtime
        rendered_lists.append(user_id)

    monkeypatch.setattr(chainlit_app, "_render_user_conversation_list", _render_stub)

    action = type("ActionStub", (), {"payload": {}})()
    asyncio.run(chainlit_app.new_conversation(action))

    assert SessionStub.get("conversation_id").startswith("conv-")
    assert SessionStub.get("conversation_id") != "conv-old"
    assert SessionStub.get("pending_thread_id") is None
    assert SessionStub.get("awaiting_edit_sql") is False
    assert SessionStub.get("last_state") is None
    assert rendered_lists == ["u-1"]
    assert sent_messages == ["Started a new conversation."]

