"""Tests for Chainlit app helpers."""

from __future__ import annotations

import asyncio

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
