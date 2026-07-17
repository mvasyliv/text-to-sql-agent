"""Gradio UI flow for the text-to-SQL agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pandas as pd
import plotly.graph_objects as go

try:
    import gradio as gr
except ModuleNotFoundError:  # pragma: no cover - exercised only in broken environments
    gr = None

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
    render_sql_preview,
)


@dataclass(frozen=True, slots=True)
class GradioViewModel:
    """Normalized Gradio render payload for one UI refresh."""

    status_message: str
    session_diagnostics: str
    conversation_choices: list[tuple[str, str]]
    conversation_value: str | None
    chat_messages: list[dict[str, str]]
    sql_markdown: str
    approval_controls_visible: bool
    edited_sql_value: str
    edited_sql_visible: bool
    submit_edited_visible: bool
    results_summary: str
    result_table: pd.DataFrame
    chart_figure: go.Figure | None
    trace_markdown: str
    trace_visible: bool
    csv_file_path: str | None
    json_file_path: str | None
    question_value: str


def _connection_config_from_env() -> dict[str, str] | None:
    sqlite_path = os.getenv("SQLITE_PATH") or os.getenv("DB_PATH")
    if not sqlite_path:
        return None
    return {"path": sqlite_path}


def _build_session_repository_from_env() -> SQLiteSessionRepository:
    settings = load_conversation_auth_settings()
    return SQLiteSessionRepository(settings.conversation_db_path)


def build_gradio_runtime() -> UiRuntime:
    """Build runtime dependencies for the Gradio UI."""
    return build_ui_runtime(
        connection_config=_connection_config_from_env(),
        session_repository=_build_session_repository_from_env(),
    )


def build_default_ui_state() -> dict[str, Any]:
    """Build deterministic default state for the Gradio UI."""
    return {
        "user_id": os.getenv("GRADIO_USER_ID", "gradio-user"),
        "display_name": os.getenv("GRADIO_DISPLAY_NAME", "Gradio User"),
        "conversation_id": f"conv-{uuid4().hex}",
        "selected_conversation_id": None,
        "pending_thread_id": None,
        "awaiting_edit_sql": False,
        "last_state": None,
        "chat_messages": [],
    }


def _clone_state(state: dict[str, Any]) -> dict[str, Any]:
    cloned_state = dict(state)
    cloned_state["chat_messages"] = list(state.get("chat_messages") or [])
    return cloned_state


def _normalize_user_profile(user_id: str, display_name: str) -> tuple[str, str]:
    normalized_user_id = user_id.strip() or "gradio-user"
    normalized_display_name = display_name.strip() or normalized_user_id
    return normalized_user_id, normalized_display_name


def _build_session_identity_diagnostics(
    conversation_id: str,
    pending_thread_id: str | None,
) -> str:
    normalized_pending_thread_id = (pending_thread_id or "").strip() or "none"
    return (
        "Session identity\n\n"
        f"- conversation_id: `{conversation_id}`\n"
        f"- pending_thread_id: `{normalized_pending_thread_id}`"
    )


def _list_user_conversations(runtime: UiRuntime, user_id: str) -> list[Any]:
    history = ConversationHistoryService(runtime.session_repository)
    return history.list_user_conversations(user_id)


def _build_conversation_choices(
    runtime: UiRuntime,
    user_id: str,
) -> list[tuple[str, str]]:
    conversations = _list_user_conversations(runtime, user_id)
    return [
        (
            render_conversation_action_label(
                item.title,
                conversation_id=item.conversation_id,
            ),
            item.conversation_id,
        )
        for item in conversations[:12]
    ]


def _conversation_value_or_empty(
    conversation_choices: list[tuple[str, str]],
    conversation_id: str,
) -> str | None:
    for _, value in conversation_choices:
        if value == conversation_id:
            return conversation_id
    return None


def _serialize_messages(messages: list[Any]) -> list[dict[str, str]]:
    serialized_messages: list[dict[str, str]] = []
    for message in messages:
        role = getattr(message.role, "value", str(message.role))
        serialized_messages.append({"role": role, "content": str(message.content)})
    return serialized_messages


def _build_execution_dataframe(execution_result: dict[str, Any]) -> pd.DataFrame:
    rows = execution_result.get("rows")
    if not isinstance(rows, list) or not rows:
        return pd.DataFrame()

    columns = execution_result.get("columns")
    if isinstance(columns, list) and columns:
        normalized_rows = [
            {str(column): row.get(column) for column in columns}
            for row in rows
            if isinstance(row, dict)
        ]
        return pd.DataFrame(normalized_rows)

    first_row = rows[0]
    if isinstance(first_row, dict):
        return pd.DataFrame(rows)

    return pd.DataFrame()


def _build_result_summary(state: dict[str, Any]) -> str:
    if state.get("status") == "rejected":
        return "SQL was rejected."

    execution_result = state.get("execution_result")
    if not isinstance(execution_result, dict):
        if state.get("last_state") is None and not state.get("error_message"):
            return ""
        return str(state.get("error_message") or "Query failed.")

    row_count = int(execution_result.get("row_count", 0) or 0)
    summary_parts = [f"Rows returned: {row_count}"]
    insight = str(state.get("insight_text") or "").strip()
    if insight:
        summary_parts.append(f"Insight: {insight}")
    return "\n\n".join(summary_parts)


def _build_sql_approval_markdown(state: dict[str, Any]) -> str:
    sql = str(state.get("generated_sql") or "")
    if not sql or not state.get("pending_thread_id"):
        return ""

    llm_notice = str(state.get("llm_user_notice") or "").strip()
    llm_status = str(state.get("llm_status") or "").strip()
    generation_mode = str(state.get("sql_generation_mode") or "Deterministic").strip()
    prefix = f"{llm_notice}\n\n" if llm_notice else ""
    status_line = f"\nLLM status: **{llm_status}**" if llm_status else ""
    return (
        f"{prefix}Proposed SQL query\n\n"
        f"Generation mode: **{generation_mode}**{status_line}\n\n"
        f"{render_sql_preview(sql)}"
    )


def _has_pending_sql_approval(state: dict[str, Any]) -> bool:
    return bool(str(state.get("generated_sql") or "").strip()) and bool(state.get("pending_thread_id"))


def _build_trace_markdown(state: dict[str, Any]) -> str:
    selected_tables = state.get("selected_tables") or []
    log_messages = state.get("log_messages") or []
    syntax_errors = state.get("syntax_errors") or []
    security_violations = state.get("security_violations") or []

    lines = ["Execution trace", ""]
    lines.append(f"- status: `{state.get('status') or 'unknown'}`")
    lines.append(f"- sql_generation_mode: `{state.get('sql_generation_mode') or 'unknown'}`")
    lines.append(f"- llm_status: `{state.get('llm_status') or 'unknown'}`")
    lines.append(f"- syntax_valid: `{state.get('syntax_valid')}`")
    lines.append(f"- security_approved: `{state.get('security_approved')}`")
    lines.append(f"- human_approved: `{state.get('human_approved')}`")
    if selected_tables:
        lines.append(f"- selected_tables: `{', '.join(str(table) for table in selected_tables)}`")
    if syntax_errors:
        lines.append("- syntax_errors:")
        lines.extend(f"  - {error}" for error in syntax_errors)
    if security_violations:
        lines.append("- security_violations:")
        lines.extend(f"  - {violation}" for violation in security_violations)
    if log_messages:
        lines.append("- log_messages:")
        lines.extend(f"  - {message}" for message in log_messages)
    return "\n".join(lines)


def _has_trace_content(state: dict[str, Any]) -> bool:
    return any(
        value is not None and value != [] and value != ""
        for value in (
            state.get("status"),
            state.get("generated_sql"),
            state.get("execution_result"),
            state.get("error_message"),
            state.get("pending_thread_id"),
            state.get("log_messages"),
            state.get("syntax_errors"),
            state.get("security_violations"),
        )
    )


def _build_export_paths(state: dict[str, Any]) -> tuple[str | None, str | None]:
    execution_result = state.get("execution_result")
    if not isinstance(execution_result, dict):
        return None, None

    exported = build_export_files(state, formats=("csv", "json"))
    return exported.get("csv"), exported.get("json")


def _build_gradio_chart_figure(chart_spec: dict[str, Any] | None) -> go.Figure | None:
    figure_payload = build_plotly_figure(chart_spec)
    if not figure_payload:
        return None
    return go.Figure(figure_payload)


def _render_view_model(
    runtime: UiRuntime,
    state: dict[str, Any],
    *,
    status_message: str = "",
) -> GradioViewModel:
    conversation_choices = _build_conversation_choices(runtime, state["user_id"])
    conversation_value = _conversation_value_or_empty(
        conversation_choices,
        str(state.get("selected_conversation_id") or state.get("conversation_id") or ""),
    )
    execution_result = state.get("execution_result")
    result_table = pd.DataFrame()
    chart_figure = None
    csv_file_path = None
    json_file_path = None

    if isinstance(execution_result, dict):
        result_table = _build_execution_dataframe(execution_result)
        chart_figure = _build_gradio_chart_figure(state.get("chart_spec"))
        csv_file_path, json_file_path = _build_export_paths(state)

    return GradioViewModel(
        status_message=status_message,
        session_diagnostics=_build_session_identity_diagnostics(
            str(state.get("conversation_id") or ""),
            state.get("pending_thread_id"),
        ),
        conversation_choices=conversation_choices,
        conversation_value=conversation_value,
        chat_messages=list(state.get("chat_messages") or []),
        sql_markdown=_build_sql_approval_markdown(state),
        approval_controls_visible=_has_pending_sql_approval(state),
        edited_sql_value=str(state.get("generated_sql") or ""),
        edited_sql_visible=bool(state.get("awaiting_edit_sql")),
        submit_edited_visible=bool(state.get("awaiting_edit_sql")),
        results_summary=_build_result_summary(state),
        result_table=result_table,
        chart_figure=chart_figure,
        trace_markdown=_build_trace_markdown(state) if _has_trace_content(state) else "",
        trace_visible=_has_trace_content(state),
        csv_file_path=csv_file_path,
        json_file_path=json_file_path,
        question_value="",
    )


def _update_view_state(
    runtime: UiRuntime,
    state: dict[str, Any],
    *,
    status_message: str = "",
) -> tuple[dict[str, Any], GradioViewModel]:
    updated_state = _clone_state(state)
    return updated_state, _render_view_model(runtime, updated_state, status_message=status_message)


def _build_refresh_payload(
    updated_state: dict[str, Any],
    view_model: GradioViewModel,
) -> list[Any]:
    conversation_update = gr.update(
        choices=view_model.conversation_choices,
        value=view_model.conversation_value,
    )
    csv_update = gr.update(value=view_model.csv_file_path, visible=bool(view_model.csv_file_path))
    json_update = gr.update(value=view_model.json_file_path, visible=bool(view_model.json_file_path))
    chart_update = gr.update(value=view_model.chart_figure, visible=bool(view_model.chart_figure))
    return [
        updated_state,
        view_model.status_message,
        view_model.session_diagnostics,
        conversation_update,
        view_model.chat_messages,
        view_model.sql_markdown,
        gr.update(visible=view_model.approval_controls_visible),
        gr.update(visible=view_model.approval_controls_visible),
        gr.update(visible=view_model.approval_controls_visible),
        gr.update(value=view_model.edited_sql_value, visible=view_model.edited_sql_visible),
        gr.update(visible=view_model.submit_edited_visible),
        view_model.results_summary,
        view_model.result_table,
        chart_update,
        gr.update(value=view_model.trace_markdown, visible=view_model.trace_visible),
        csv_update,
        json_update,
        view_model.question_value,
    ]


def handle_apply_user(
    runtime: UiRuntime,
    state: dict[str, Any],
    user_id: str,
    display_name: str,
) -> tuple[dict[str, Any], GradioViewModel]:
    updated_state = _clone_state(state)
    normalized_user_id, normalized_display_name = _normalize_user_profile(user_id, display_name)
    identity_changed = normalized_user_id != updated_state.get("user_id")

    if identity_changed:
        updated_state.update(
            {
                "conversation_id": f"conv-{uuid4().hex}",
                "selected_conversation_id": None,
                "pending_thread_id": None,
                "awaiting_edit_sql": False,
                "last_state": None,
                "chat_messages": [],
            }
        )

    updated_state["user_id"] = normalized_user_id
    updated_state["display_name"] = normalized_display_name
    return _update_view_state(runtime, updated_state, status_message="Applied user profile.")


def handle_start_new_conversation(
    runtime: UiRuntime,
    state: dict[str, Any],
) -> tuple[dict[str, Any], GradioViewModel]:
    updated_state = _clone_state(state)
    updated_state.update(
        {
            "conversation_id": f"conv-{uuid4().hex}",
            "selected_conversation_id": None,
            "pending_thread_id": None,
            "awaiting_edit_sql": False,
            "last_state": None,
            "chat_messages": [],
        }
    )
    return _update_view_state(runtime, updated_state, status_message="Started a new conversation.")


def handle_load_selected_conversation(
    runtime: UiRuntime,
    state: dict[str, Any],
    selected_conversation_id: str | None,
) -> tuple[dict[str, Any], GradioViewModel]:
    if not selected_conversation_id:
        return _update_view_state(runtime, state, status_message="Choose a saved conversation first.")

    history = ConversationHistoryService(runtime.session_repository)
    try:
        record = history.load_user_conversation(
            user_id=str(state.get("user_id") or ""),
            conversation_id=selected_conversation_id,
        )
    except ConversationAccessError:
        return _update_view_state(runtime, state, status_message="Conversation not found for this user.")

    updated_state = _clone_state(state)
    updated_state.update(
        {
            "conversation_id": record.conversation.conversation_id,
            "selected_conversation_id": record.conversation.conversation_id,
            "pending_thread_id": record.conversation.graph_thread_id,
            "awaiting_edit_sql": False,
            "last_state": None,
            "chat_messages": _serialize_messages(record.messages[-16:]),
        }
    )
    return _update_view_state(
        runtime,
        updated_state,
        status_message=f"Opened conversation: {record.conversation.title}.",
    )


def _append_query_result(
    runtime: UiRuntime,
    state: dict[str, Any],
    *,
    status_message: str,
) -> tuple[dict[str, Any], GradioViewModel]:
    updated_state = _clone_state(state)
    result_summary = _build_result_summary(updated_state)
    if result_summary:
        updated_state["chat_messages"].append({"role": "assistant", "content": result_summary})
    return _update_view_state(runtime, updated_state, status_message=status_message)


def handle_send_question(
    runtime: UiRuntime,
    state: dict[str, Any],
    question: str,
) -> tuple[dict[str, Any], GradioViewModel]:
    normalized_question = question.strip()
    if not normalized_question:
        return _update_view_state(runtime, state, status_message="Please enter a non-empty question.")

    updated_state = _clone_state(state)
    updated_state["chat_messages"].append({"role": "user", "content": normalized_question})

    turn = start_query_turn(
        runtime,
        user_id=str(updated_state["user_id"]),
        conversation_id=str(updated_state["conversation_id"]),
        user_question=normalized_question,
    )
    updated_state["pending_thread_id"] = turn.thread_id
    updated_state["last_state"] = turn.state
    updated_state.update(turn.state)

    if turn.awaiting_approval:
        updated_state["chat_messages"].append(
            {"role": "assistant", "content": _build_sql_approval_markdown(turn.state)}
        )
        updated_state["awaiting_edit_sql"] = False
        return _update_view_state(runtime, updated_state, status_message="Review the SQL before execution.")

    return _append_query_result(runtime, updated_state, status_message="Query completed.")


def handle_resume_with_decision(
    runtime: UiRuntime,
    state: dict[str, Any],
    decision: str | dict[str, str],
) -> tuple[dict[str, Any], GradioViewModel]:
    thread_id = str(state.get("pending_thread_id") or "").strip()
    if not thread_id:
        return _update_view_state(runtime, state, status_message="No pending SQL query to continue.")

    updated_state = _clone_state(state)
    result = resume_query_turn(
        runtime,
        conversation_id=str(updated_state["conversation_id"]),
        thread_id=thread_id,
        decision=decision,
    )
    updated_state["pending_thread_id"] = None
    updated_state["awaiting_edit_sql"] = False
    updated_state["last_state"] = result
    updated_state["chat_messages"].append({"role": "assistant", "content": _build_result_summary(result)})
    updated_state.update(result)
    return _update_view_state(runtime, updated_state, status_message="SQL decision applied.")


def handle_begin_sql_edit(
    runtime: UiRuntime,
    state: dict[str, Any],
) -> tuple[dict[str, Any], GradioViewModel]:
    updated_state = _clone_state(state)
    updated_state["awaiting_edit_sql"] = True
    return _update_view_state(runtime, updated_state, status_message="Edit the proposed SQL and resubmit.")


def handle_submit_edited_sql(
    runtime: UiRuntime,
    state: dict[str, Any],
    edited_sql: str,
) -> tuple[dict[str, Any], GradioViewModel]:
    normalized_sql = edited_sql.strip()
    if not normalized_sql:
        return _update_view_state(runtime, state, status_message="Edited SQL cannot be empty.")

    return handle_resume_with_decision(runtime, state, {"edit": normalized_sql})


def create_app() -> Any:
    """Build the Gradio Blocks app."""
    if gr is None:  # pragma: no cover - only reachable in broken environments
        raise RuntimeError("Gradio is unavailable. Install dependencies with 'uv sync'.")

    runtime = build_gradio_runtime()
    initial_state = build_default_ui_state()
    initial_view_model = _render_view_model(runtime, initial_state)

    with gr.Blocks(title="Text-to-SQL Agent") as demo:
        state = gr.State(initial_state)

        gr.Markdown("# Text-to-SQL Agent")
        gr.Markdown("Ask a natural-language question, review SQL before execution, and inspect the results.")

        status_banner = gr.Markdown(initial_view_model.status_message)

        with gr.Row():
            with gr.Column(scale=1, min_width=280):
                gr.Markdown("## Session")
                user_id_input = gr.Textbox(label="User ID", value=initial_state["user_id"])
                display_name_input = gr.Textbox(label="Display Name", value=initial_state["display_name"])
                apply_user_button = gr.Button("Apply User", variant="primary")
                session_diagnostics = gr.Markdown(
                    initial_view_model.session_diagnostics
                )
                new_conversation_button = gr.Button("Start New Conversation")
                conversation_dropdown = gr.Dropdown(
                    label="Open conversation",
                    choices=initial_view_model.conversation_choices,
                    value=initial_view_model.conversation_value,
                )
                load_conversation_button = gr.Button("Load Selected")

            with gr.Column(scale=2, min_width=520):
                gr.Markdown("## Conversation")
                chatbot = gr.Chatbot(value=initial_view_model.chat_messages, label="Conversation", height=360)
                question_input = gr.Textbox(
                    label="Ask a database question",
                    placeholder="For example: How many users signed up last week?",
                    value=initial_view_model.question_value,
                )
                send_question_button = gr.Button("Send", variant="primary")

                sql_markdown = gr.Markdown(initial_view_model.sql_markdown)

                with gr.Row():
                    approve_button = gr.Button(
                        "Approve",
                        variant="primary",
                        visible=initial_view_model.approval_controls_visible,
                    )
                    reject_button = gr.Button(
                        "Reject",
                        visible=initial_view_model.approval_controls_visible,
                    )
                    edit_button = gr.Button(
                        "Edit",
                        visible=initial_view_model.approval_controls_visible,
                    )

                edited_sql_input = gr.Textbox(
                    label="Edited SQL",
                    lines=8,
                    value=initial_view_model.edited_sql_value,
                    visible=initial_view_model.edited_sql_visible,
                    placeholder="Update the SQL proposal and resubmit it.",
                )
                submit_edited_sql_button = gr.Button(
                    "Submit Edited SQL",
                    variant="primary",
                    visible=initial_view_model.submit_edited_visible,
                )

                with gr.Tabs():
                    with gr.Tab("Results"):
                        results_summary = gr.Markdown(initial_view_model.results_summary)
                        result_table = gr.Dataframe(label="Query result", interactive=False, value=initial_view_model.result_table)
                    with gr.Tab("Chart"):
                        chart_plot = gr.Plot(value=initial_view_model.chart_figure, visible=bool(initial_view_model.chart_figure))
                    with gr.Tab("Trace"):
                        trace_markdown = gr.Markdown(
                            initial_view_model.trace_markdown,
                            visible=initial_view_model.trace_visible,
                        )
                    with gr.Tab("Export"):
                        csv_file = gr.File(label="CSV export", value=initial_view_model.csv_file_path, visible=bool(initial_view_model.csv_file_path))
                        json_file = gr.File(label="JSON export", value=initial_view_model.json_file_path, visible=bool(initial_view_model.json_file_path))

        refresh_outputs = [
            state,
            status_banner,
            session_diagnostics,
            conversation_dropdown,
            chatbot,
            sql_markdown,
            approve_button,
            reject_button,
            edit_button,
            edited_sql_input,
            submit_edited_sql_button,
            results_summary,
            result_table,
            chart_plot,
            trace_markdown,
            csv_file,
            json_file,
            question_input,
        ]

        def _refresh_view(
            updated_state: dict[str, Any],
            view_model: GradioViewModel,
        ) -> list[Any]:
            return _build_refresh_payload(updated_state, view_model)

        apply_user_button.click(
            fn=lambda user_id, display_name, current_state: _refresh_view(
                *handle_apply_user(runtime, current_state, user_id, display_name)
            ),
            inputs=[user_id_input, display_name_input, state],
            outputs=refresh_outputs,
        )

        new_conversation_button.click(
            fn=lambda current_state: _refresh_view(*handle_start_new_conversation(runtime, current_state)),
            inputs=[state],
            outputs=refresh_outputs,
        )

        load_conversation_button.click(
            fn=lambda selected_id, current_state: _refresh_view(
                *handle_load_selected_conversation(runtime, current_state, selected_id)
            ),
            inputs=[conversation_dropdown, state],
            outputs=refresh_outputs,
        )

        send_question_button.click(
            fn=lambda question, current_state: _refresh_view(
                *handle_send_question(runtime, current_state, question)
            ),
            inputs=[question_input, state],
            outputs=refresh_outputs,
        )

        approve_button.click(
            fn=lambda current_state: _refresh_view(
                *handle_resume_with_decision(runtime, current_state, "approve")
            ),
            inputs=[state],
            outputs=refresh_outputs,
        )

        reject_button.click(
            fn=lambda current_state: _refresh_view(
                *handle_resume_with_decision(runtime, current_state, "reject")
            ),
            inputs=[state],
            outputs=refresh_outputs,
        )

        edit_button.click(
            fn=lambda current_state: _refresh_view(*handle_begin_sql_edit(runtime, current_state)),
            inputs=[state],
            outputs=refresh_outputs,
        )

        submit_edited_sql_button.click(
            fn=lambda edited_sql, current_state: _refresh_view(
                *handle_submit_edited_sql(runtime, current_state, edited_sql)
            ),
            inputs=[edited_sql_input, state],
            outputs=refresh_outputs,
        )

        demo.load(
            fn=lambda current_state: _refresh_view(*_update_view_state(runtime, current_state)),
            inputs=[state],
            outputs=refresh_outputs,
        )

    return demo
