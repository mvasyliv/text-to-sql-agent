"""Streamlit chat UI for the text-to-SQL workflow."""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from text_to_sql_agent.config.settings import load_conversation_auth_settings
from text_to_sql_agent.repositories.sqlite_session_repository import SQLiteSessionRepository
from text_to_sql_agent.services.conversation_history_service import (
    ConversationAccessError,
    ConversationHistoryService,
)
from text_to_sql_agent.ui.handlers import (
    UiRuntime,
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

import streamlit as st


def _connection_config_from_env() -> dict[str, str] | None:
    sqlite_path = os.getenv("SQLITE_PATH") or os.getenv("DB_PATH")
    if not sqlite_path:
        return None
    return {"path": sqlite_path}


def _build_session_repository_from_env() -> SQLiteSessionRepository:
    settings = load_conversation_auth_settings()
    return SQLiteSessionRepository(settings.conversation_db_path)


def _get_runtime() -> UiRuntime:
    runtime = st.session_state.get("runtime")
    if runtime is None:
        runtime = build_ui_runtime(
            connection_config=_connection_config_from_env(),
            session_repository=_build_session_repository_from_env(),
        )
        st.session_state["runtime"] = runtime
    return runtime


def _build_result_render_model(state: dict[str, Any]) -> dict[str, Any]:
    execution_result = state.get("execution_result")
    if not isinstance(execution_result, dict):
        return {
            "ok": False,
            "error_message": str(state.get("error_message") or "Query failed."),
        }

    return {
        "ok": True,
        "row_count": int(execution_result.get("row_count", 0) or 0),
        "table_markdown": render_markdown_table(execution_result),
        "insight": str(state.get("insight_text") or "").strip(),
        "chart_figure": build_plotly_figure(state.get("chart_spec")),
    }


def _build_sql_approval_markdown(state: dict[str, Any]) -> str:
    sql = str(state.get("generated_sql") or "")
    llm_notice = str(state.get("llm_user_notice") or "").strip()
    generation_mode = str(state.get("sql_generation_mode") or "Deterministic").strip()
    prefix = f"{llm_notice}\n\n" if llm_notice else ""
    return (
        f"{prefix}Proposed SQL query\n\n"
        f"Generation mode: **{generation_mode}**\n\n"
        f"{render_sql_preview(sql)}"
    )


def _append_chat_message(role: str, content: str) -> None:
    st.session_state["chat_messages"].append({"role": role, "content": content})


def _set_active_conversation(conversation_id: str) -> None:
    st.session_state["conversation_id"] = conversation_id
    st.session_state["pending_thread_id"] = None
    st.session_state["awaiting_edit_sql"] = False
    st.session_state["last_state"] = None
    st.session_state["chat_messages"] = []


def _ensure_streamlit_session_defaults() -> None:
    st.session_state.setdefault("user_id", os.getenv("STREAMLIT_USER_ID", "streamlit-user"))
    st.session_state.setdefault("display_name", os.getenv("STREAMLIT_DISPLAY_NAME", "Streamlit User"))
    st.session_state.setdefault("conversation_id", f"conv-{uuid4().hex}")
    st.session_state.setdefault("pending_thread_id", None)
    st.session_state.setdefault("awaiting_edit_sql", False)
    st.session_state.setdefault("last_state", None)
    st.session_state.setdefault("chat_messages", [])


def _submit_user_question(runtime: UiRuntime, question: str) -> None:
    user_id = str(st.session_state["user_id"])
    conversation_id = str(st.session_state["conversation_id"])
    _append_chat_message("user", question)

    turn = start_query_turn(
        runtime,
        user_id=user_id,
        conversation_id=conversation_id,
        user_question=question,
    )
    st.session_state["pending_thread_id"] = turn.thread_id
    st.session_state["last_state"] = turn.state

    if turn.awaiting_approval:
        _append_chat_message("assistant", _build_sql_approval_markdown(turn.state))
        return

    _append_query_result(turn.state)


def _append_query_result(state: dict[str, Any]) -> None:
    render_model = _build_result_render_model(state)
    if not render_model["ok"]:
        _append_chat_message("assistant", render_model["error_message"])
        return

    _append_chat_message("assistant", f"Rows returned: {render_model['row_count']}")
    _append_chat_message("assistant", render_model["table_markdown"])
    if render_model["insight"]:
        _append_chat_message("assistant", f"Insight: {render_model['insight']}")


def _resume_with_decision(runtime: UiRuntime, decision: str | dict[str, str]) -> None:
    thread_id = st.session_state.get("pending_thread_id")
    conversation_id = str(st.session_state["conversation_id"])
    if not thread_id:
        st.warning("No pending SQL query to continue.")
        return

    state = resume_query_turn(
        runtime,
        conversation_id=conversation_id,
        thread_id=str(thread_id),
        decision=decision,
    )
    st.session_state["pending_thread_id"] = None
    st.session_state["awaiting_edit_sql"] = False
    st.session_state["last_state"] = state
    _append_query_result(state)


def _render_history_sidebar(runtime: UiRuntime) -> None:
    st.sidebar.subheader("Conversation History")
    history = ConversationHistoryService(runtime.session_repository)
    user_id = str(st.session_state["user_id"])
    conversations = history.list_user_conversations(user_id)

    if st.sidebar.button("Start New Conversation", use_container_width=True):
        _set_active_conversation(f"conv-{uuid4().hex}")
        st.rerun()

    if not conversations:
        st.sidebar.caption("No saved conversations yet.")
        return

    options = {
        render_conversation_action_label(item.title, conversation_id=item.conversation_id): item.conversation_id
        for item in conversations[:12]
    }
    selected_label = st.sidebar.selectbox("Open conversation", options=list(options.keys()))
    if st.sidebar.button("Load Selected", use_container_width=True):
        conversation_id = options[selected_label]
        try:
            record = history.load_user_conversation(user_id=user_id, conversation_id=conversation_id)
        except ConversationAccessError:
            st.sidebar.error("Conversation not found for this user.")
            return
        _set_active_conversation(record.conversation.conversation_id)
        for message in record.messages[-16:]:
            role = "assistant" if message.role.value != "user" else "user"
            _append_chat_message(role, message.content)
        st.rerun()


def _render_pending_sql_controls(runtime: UiRuntime) -> None:
    thread_id = st.session_state.get("pending_thread_id")
    if not thread_id:
        return

    state = st.session_state.get("last_state") or {}
    sql_preview = str(state.get("generated_sql") or "")
    if not sql_preview:
        return

    st.divider()
    st.subheader("SQL Approval")
    st.markdown(_build_sql_approval_markdown(state))

    approve_col, reject_col, edit_col = st.columns(3)
    if approve_col.button("Approve", use_container_width=True):
        _resume_with_decision(runtime, "approve")
        st.rerun()
    if reject_col.button("Reject", use_container_width=True):
        _resume_with_decision(runtime, "reject")
        st.rerun()
    if edit_col.button("Edit", use_container_width=True):
        st.session_state["awaiting_edit_sql"] = True

    if st.session_state.get("awaiting_edit_sql"):
        edited_sql = st.text_area("Edited SQL", value=sql_preview, height=180)
        if st.button("Submit Edited SQL", use_container_width=True):
            _resume_with_decision(runtime, {"edit": edited_sql})
            st.rerun()


def _render_export_controls() -> None:
    state = st.session_state.get("last_state") or {}
    execution_result = state.get("execution_result")
    if not isinstance(execution_result, dict):
        return

    st.divider()
    st.subheader("Export")
    csv_col, json_col = st.columns(2)
    if csv_col.button("Export CSV", use_container_width=True):
        path = build_export_files(state, formats=("csv",))["csv"]
        st.success(f"CSV exported to: {path}")
    if json_col.button("Export JSON", use_container_width=True):
        path = build_export_files(state, formats=("json",))["json"]
        st.success(f"JSON exported to: {path}")


def _render_chart_if_present() -> None:
    state = st.session_state.get("last_state") or {}
    chart_figure = build_plotly_figure(state.get("chart_spec"))
    if chart_figure:
        st.plotly_chart(chart_figure, use_container_width=True)


def main() -> None:

    st.set_page_config(page_title="Text-to-SQL Agent", page_icon=":bar_chart:", layout="wide")
    st.title("Text-to-SQL Agent")
    st.caption("Ask a natural-language question; review SQL before execution.")

    _ensure_streamlit_session_defaults()
    runtime = _get_runtime()
    _render_history_sidebar(runtime)

    for message in st.session_state["chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a database question")
    if question and question.strip():
        _submit_user_question(runtime, question.strip())
        st.rerun()

    _render_pending_sql_controls(runtime)
    _render_export_controls()
    _render_chart_if_present()


if __name__ == "__main__":
    main()

