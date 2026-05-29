"""Chainlit chat flow for the DB assistant."""

from __future__ import annotations

import os
from uuid import uuid4

from text_to_sql_agent.config.settings import load_conversation_auth_settings
from text_to_sql_agent.repositories.sqlite_session_repository import SQLiteSessionRepository
from text_to_sql_agent.services import ConversationHistoryService
from text_to_sql_agent.services.conversation_history_service import (
    ConversationAccessError,
    ConversationHistoryRecord,
)
from text_to_sql_agent.ui.auth_callbacks import (
    authenticate_with_password,
    build_auth_service_from_env,
    make_chainlit_user,
)
from text_to_sql_agent.ui.handlers import (
    QueryTurnResult,
    build_export_files,
    build_ui_runtime,
    resume_query_turn,
    start_query_turn,
)
from text_to_sql_agent.ui.renderers import (
    build_plotly_figure,
    render_conversation_action_label,
    render_markdown_table,
    render_sql_preview,
)

try:
    import chainlit as cl
except ModuleNotFoundError:  # pragma: no cover - tested through import without chainlit
    cl = None

# Auth service is built once at module level and shared across requests.
_auth_service = None


def _get_auth_service():
    global _auth_service
    if _auth_service is None:
        _auth_service = build_auth_service_from_env()
    return _auth_service


def _connection_config_from_env() -> dict | None:
    sqlite_path = os.getenv("SQLITE_PATH") or os.getenv("DB_PATH")
    if not sqlite_path:
        return None
    return {"path": sqlite_path}


def _get_runtime():
    runtime = cl.user_session.get("runtime")
    if runtime is None:
        runtime = build_ui_runtime(
            connection_config=_connection_config_from_env(),
            session_repository=_build_session_repository_from_env(),
        )
        cl.user_session.set("runtime", runtime)
    return runtime


def _build_session_repository_from_env() -> SQLiteSessionRepository:
    settings = load_conversation_auth_settings()
    return SQLiteSessionRepository(settings.conversation_db_path)


def _resolve_authenticated_identity() -> tuple[str, str, str]:
    """Resolve `(user_id, username, display_name)` from Chainlit session user."""
    session_user = cl.user_session.get("user")
    if session_user is None:
        return ("anonymous", "anonymous", "Anonymous")

    user_id = str(getattr(session_user, "identifier", "") or "").strip() or "anonymous"
    metadata = getattr(session_user, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    username = str(metadata.get("username") or user_id).strip() or user_id
    display_name = (
        str(getattr(session_user, "display_name", "") or metadata.get("display_name") or username)
        .strip()
        or username
    )
    return (user_id, username, display_name)


def _build_history_actions(conversations: list, *, max_actions: int = 8) -> list:
    actions = []
    for conversation in conversations[:max_actions]:
        label = render_conversation_action_label(
            conversation.title,
            conversation_id=conversation.conversation_id,
        )
        actions.append(
            cl.Action(
                name="open_conversation",
                payload={"conversation_id": conversation.conversation_id},
                label=label,
            )
        )
    return actions


def _build_new_conversation_action():
    return cl.Action(
        name="new_conversation",
        payload={},
        label="Start new conversation",
    )


def _set_active_conversation(conversation_id: str) -> None:
    cl.user_session.set("conversation_id", conversation_id)
    cl.user_session.set("pending_thread_id", None)
    cl.user_session.set("awaiting_edit_sql", False)
    cl.user_session.set("last_state", None)


async def _render_loaded_conversation_messages(
    record: ConversationHistoryRecord,
    *,
    max_messages: int = 12,
) -> None:
    if not record.messages:
        await cl.Message(content="This conversation has no messages yet.").send()
        return

    role_labels = {
        "user": "User",
        "assistant": "Assistant",
        "tool": "Tool",
        "system": "System",
    }
    visible_messages = record.messages[-max_messages:]
    lines = [
        f"**{role_labels.get(message.role.value, message.role.value.title())}:** {message.content}"
        for message in visible_messages
    ]
    prefix = ""
    if len(record.messages) > max_messages:
        prefix = f"Showing latest {max_messages} of {len(record.messages)} messages.\n\n"
    await cl.Message(content=prefix + "\n\n".join(lines)).send()


async def _render_user_conversation_list(runtime, *, user_id: str) -> None:
    history = ConversationHistoryService(runtime.session_repository)
    conversations = history.list_user_conversations(user_id)
    new_conversation_action = _build_new_conversation_action()
    if not conversations:
        await cl.Message(
            content="No previous conversations yet. Start a new conversation.",
            actions=[new_conversation_action],
        ).send()
        return

    actions = [new_conversation_action, *_build_history_actions(conversations)]
    count = len(conversations)
    shown_history_count = len(actions) - 1
    suffix = "" if count <= shown_history_count else f" Showing latest {shown_history_count}."
    await cl.Message(
        content=f"Recent conversations ({count}). Select one to open or start a new one.{suffix}",
        actions=actions,
    ).send()


async def _render_sql_approval(turn: QueryTurnResult) -> None:
    sql = str(turn.state.get("generated_sql") or "")
    llm_notice = str(turn.state.get("llm_user_notice") or "").strip()
    generation_mode = str(turn.state.get("sql_generation_mode") or "Deterministic").strip()
    actions = [
        cl.Action(name="approve_sql", payload={}, label="Approve"),
        cl.Action(name="reject_sql", payload={}, label="Reject"),
        cl.Action(name="edit_sql", payload={}, label="Edit"),
    ]
    prefix = f"{llm_notice}\n\n" if llm_notice else ""
    await cl.Message(
        content=(
            f"{prefix}Proposed SQL query:\n"
            f"Generation mode: **{generation_mode}**\n\n"
            f"{render_sql_preview(sql)}\n\n"
            "Choose one action: approve, reject, or edit."
        ),
        actions=actions,
    ).send()


def _build_chart_elements(chart_figure: dict | None) -> list:
    """Build chart elements when Chainlit and Plotly support are available."""
    if not chart_figure or not hasattr(cl, "Plotly"):
        return []

    try:
        return [cl.Plotly(name="query_chart", figure=chart_figure, display="inline")]
    except ModuleNotFoundError:
        return []


async def _render_query_result(state: dict) -> None:
    execution_result = state.get("execution_result")
    if not isinstance(execution_result, dict):
        message = state.get("error_message") or "Query failed."
        await cl.Message(content=message).send()
        return

    row_count = execution_result.get("row_count", 0)
    insight = state.get("insight_text") or ""

    await cl.Message(content=f"Rows returned: {row_count}").send()

    table_markdown = render_markdown_table(execution_result)
    await cl.Message(content=table_markdown).send()

    export_actions = [
        cl.Action(name="export_csv", payload={}, label="Export CSV"),
        cl.Action(name="export_json", payload={}, label="Export JSON"),
    ]

    if insight:
        await cl.Message(content=f"Insight: {insight}\n\n**Export results:**", actions=export_actions).send()
    else:
        await cl.Message(content="**Export results:**", actions=export_actions).send()

    chart_figure = build_plotly_figure(state.get("chart_spec"))
    chart_elements = _build_chart_elements(chart_figure)
    if chart_elements:
        await cl.Message(
            content="One-shot chart",
            elements=chart_elements,
        ).send()


if cl is not None:

    @cl.password_auth_callback
    async def password_auth_callback(username: str, password: str):
        """Authenticate the user via username/password using AuthService.

        Returns a ``cl.User`` on success, ``None`` to reject the login.
        The Chainlit framework shows an error message automatically when
        ``None`` is returned.
        """
        principal = await authenticate_with_password(
            username, password, _get_auth_service()
        )
        if principal is None:
            return None
        return make_chainlit_user(principal)

    @cl.on_chat_start
    async def on_chat_start() -> None:
        runtime = _get_runtime()
        user_id, username, display_name = _resolve_authenticated_identity()
        cl.user_session.set("user_id", user_id)
        cl.user_session.set("username", username)
        cl.user_session.set("display_name", display_name)
        _set_active_conversation(f"conv-{uuid4().hex}")

        await cl.Message(
            content=(
                f"DB assistant is ready, {display_name}. "
                "Ask a natural-language question and I will "
                "show SQL preview before execution."
            )
        ).send()
        await _render_user_conversation_list(runtime, user_id=user_id)


    @cl.on_message
    async def on_message(message: cl.Message) -> None:
        runtime = _get_runtime()
        user_id = cl.user_session.get("user_id")
        conversation_id = cl.user_session.get("conversation_id")
        pending_thread_id = cl.user_session.get("pending_thread_id")
        awaiting_edit_sql = bool(cl.user_session.get("awaiting_edit_sql"))
        content = str(message.content or "").strip()

        if awaiting_edit_sql and pending_thread_id:
            cl.user_session.set("awaiting_edit_sql", False)
            state = resume_query_turn(
                runtime,
                conversation_id=conversation_id,
                thread_id=pending_thread_id,
                decision={"edit": content},
            )
            cl.user_session.set("pending_thread_id", None)
            cl.user_session.set("last_state", state)
            await _render_query_result(state)
            return

        if not content:
            await cl.Message(content="Please send a non-empty message.").send()
            return

        turn = start_query_turn(
            runtime,
            user_id=user_id,
            conversation_id=conversation_id,
            user_question=content,
        )
        cl.user_session.set("pending_thread_id", turn.thread_id)
        cl.user_session.set("last_state", turn.state)

        if turn.awaiting_approval:
            await _render_sql_approval(turn)
            return

        await _render_query_result(turn.state)


    @cl.action_callback("approve_sql")
    async def approve_sql(_: cl.Action) -> None:
        runtime = _get_runtime()
        thread_id = cl.user_session.get("pending_thread_id")
        conversation_id = cl.user_session.get("conversation_id")
        if not thread_id:
            await cl.Message(content="No pending query to approve.").send()
            return

        state = resume_query_turn(
            runtime,
            conversation_id=conversation_id,
            thread_id=thread_id,
            decision="approve",
        )
        cl.user_session.set("pending_thread_id", None)
        cl.user_session.set("last_state", state)
        await _render_query_result(state)


    @cl.action_callback("reject_sql")
    async def reject_sql(_: cl.Action) -> None:
        runtime = _get_runtime()
        thread_id = cl.user_session.get("pending_thread_id")
        conversation_id = cl.user_session.get("conversation_id")
        if not thread_id:
            await cl.Message(content="No pending query to reject.").send()
            return

        state = resume_query_turn(
            runtime,
            conversation_id=conversation_id,
            thread_id=thread_id,
            decision="reject",
        )
        cl.user_session.set("pending_thread_id", None)
        cl.user_session.set("last_state", state)
        await cl.Message(content="Query rejected.").send()
        await _render_query_result(state)


    @cl.action_callback("edit_sql")
    async def edit_sql(_: cl.Action) -> None:
        thread_id = cl.user_session.get("pending_thread_id")
        if not thread_id:
            await cl.Message(content="No pending query to edit.").send()
            return

        cl.user_session.set("awaiting_edit_sql", True)
        await cl.Message(content="Send the edited SQL as your next message.").send()


    @cl.action_callback("open_conversation")
    async def open_conversation(action: cl.Action) -> None:
        runtime = _get_runtime()
        user_id = str(cl.user_session.get("user_id") or "").strip()
        payload = getattr(action, "payload", None) or {}
        if not isinstance(payload, dict):
            payload = {}
        conversation_id = str(payload.get("conversation_id") or "").strip()
        if not conversation_id:
            await cl.Message(content="Conversation ID is missing.").send()
            return

        history = ConversationHistoryService(runtime.session_repository)
        try:
            record = history.load_user_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
            )
        except ConversationAccessError:
            await cl.Message(content="Conversation not found for this user.").send()
            return

        _set_active_conversation(record.conversation.conversation_id)
        label = render_conversation_action_label(
            record.conversation.title,
            conversation_id=record.conversation.conversation_id,
        )
        await cl.Message(content=f"Opened conversation: {label}.").send()
        await _render_loaded_conversation_messages(record)


    @cl.action_callback("new_conversation")
    async def new_conversation(_: cl.Action) -> None:
        runtime = _get_runtime()
        user_id = str(cl.user_session.get("user_id") or "").strip()
        conversation_id = f"conv-{uuid4().hex}"
        _set_active_conversation(conversation_id)
        await cl.Message(content="Started a new conversation.").send()
        await _render_user_conversation_list(runtime, user_id=user_id)


    @cl.action_callback("export_csv")
    async def export_csv(_: cl.Action) -> None:
        state = cl.user_session.get("last_state") or {}
        try:
            path = build_export_files(state, formats=("csv",))["csv"]
            await cl.Message(content=f"CSV exported to: {path}").send()
        except Exception as exc:  # noqa: BLE001
            await cl.Message(content=f"CSV export failed: {exc}").send()


    @cl.action_callback("export_json")
    async def export_json(_: cl.Action) -> None:
        state = cl.user_session.get("last_state") or {}
        try:
            path = build_export_files(state, formats=("json",))["json"]
            await cl.Message(content=f"JSON exported to: {path}").send()
        except Exception as exc:  # noqa: BLE001
            await cl.Message(content=f"JSON export failed: {exc}").send()
