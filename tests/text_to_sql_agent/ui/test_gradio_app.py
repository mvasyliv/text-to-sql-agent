"""Focused tests for the Gradio UI helpers."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from text_to_sql_agent.models.session import Conversation
from text_to_sql_agent.repositories.session_repository import InMemorySessionRepository
from text_to_sql_agent.ui.handlers import QueryTurnResult
from text_to_sql_agent.ui.gradio_app import (
    GradioViewModel,
    _build_refresh_payload,
    _build_session_identity_diagnostics,
    _build_gradio_chart_figure,
    _has_trace_content,
    _has_pending_sql_approval,
    _build_sql_approval_markdown,
    _render_view_model,
    build_default_ui_state,
    build_gradio_runtime,
    handle_load_selected_conversation,
    handle_apply_user,
    handle_resume_with_decision,
    handle_send_question,
    handle_start_new_conversation,
)


def test_build_default_ui_state_sets_safe_defaults() -> None:
    state = build_default_ui_state()

    assert state["user_id"] == "gradio-user"
    assert state["display_name"] == "Gradio User"
    assert state["pending_thread_id"] is None
    assert state["chat_messages"] == []


def test_build_session_identity_diagnostics_handles_missing_thread_id() -> None:
    content = _build_session_identity_diagnostics("conv-123", None)

    assert "conversation_id: `conv-123`" in content
    assert "pending_thread_id: `none`" in content


def test_build_sql_approval_markdown_includes_status_and_mode() -> None:
    content = _build_sql_approval_markdown(
        {
            "generated_sql": "SELECT 1;",
            "llm_user_notice": "LLM fallback was used.",
            "sql_generation_mode": "Few-shot fallback",
            "llm_status": "missing_api_key",
            "pending_thread_id": "thread-1",
        }
    )

    assert "LLM fallback was used." in content
    assert "Generation mode: **Few-shot fallback**" in content
    assert "LLM status: **missing_api_key**" in content
    assert "```sql" in content


def test_has_pending_sql_approval_requires_sql_and_thread() -> None:
    assert not _has_pending_sql_approval({"generated_sql": "SELECT 1;", "pending_thread_id": None})
    assert not _has_pending_sql_approval({"generated_sql": "", "pending_thread_id": "thread-1"})
    assert _has_pending_sql_approval({"generated_sql": "SELECT 1;", "pending_thread_id": "thread-1"})


def test_has_trace_content_skips_idle_state() -> None:
    assert not _has_trace_content({})
    assert not _has_trace_content({"status": None, "log_messages": [], "generated_sql": ""})
    assert _has_trace_content({"status": "pending"})


def test_build_gradio_chart_figure_returns_plotly_figure() -> None:
    figure = _build_gradio_chart_figure(
        {
            "type": "bar",
            "title": "Query chart",
            "x": ["A", "B"],
            "y": [1, 2],
        }
    )

    assert isinstance(figure, go.Figure)
    assert figure.layout.title.text == "Query chart"


def test_build_refresh_payload_keeps_result_table_and_trace_positions() -> None:
    state = build_default_ui_state()
    view_model = GradioViewModel(
        status_message="status",
        session_diagnostics="diagnostics",
        conversation_choices=[("Conversation", "conv-1")],
        conversation_value="conv-1",
        chat_messages=[{"role": "assistant", "content": "hello"}],
        sql_markdown="sql",
        approval_controls_visible=False,
        edited_sql_value="SELECT 1;",
        edited_sql_visible=False,
        submit_edited_visible=False,
        results_summary="Rows returned: 1",
        result_table=pd.DataFrame([{"value": 1}]),
        chart_figure=go.Figure(),
        trace_markdown="Execution trace",
        trace_visible=True,
        csv_file_path="/tmp/result.csv",
        json_file_path="/tmp/result.json",
        question_value="",
    )

    payload = _build_refresh_payload(state, view_model)

    assert len(payload) == 18
    assert payload[12].equals(view_model.result_table)
    assert payload[14]["value"] == "Execution trace"
    assert payload[15]["value"] == "/tmp/result.csv"
    assert payload[16]["value"] == "/tmp/result.json"


def test_render_view_model_loads_saved_conversation_choices() -> None:
    runtime = type(
        "Runtime",
        (),
        {"graph": object(), "session_repository": InMemorySessionRepository()},
    )()
    runtime.session_repository.save_conversation(
        Conversation(
            conversation_id="conv-history-1",
            user_id="history-user",
            title="Saved conversation",
            graph_thread_id="thread-history-1",
        )
    )

    state = build_default_ui_state()
    state["user_id"] = "history-user"
    state["display_name"] = "History User"

    view_model = _render_view_model(runtime, state)

    assert view_model.conversation_choices == [("Saved conversation", "conv-history-1")]
    assert view_model.conversation_value is None


def test_render_view_model_keeps_result_panels_empty_for_idle_state() -> None:
    runtime = type(
        "Runtime",
        (),
        {"graph": object(), "session_repository": InMemorySessionRepository()},
    )()
    view_model = _render_view_model(runtime, build_default_ui_state())

    assert view_model.results_summary == ""
    assert view_model.result_table.empty
    assert view_model.chart_figure is None
    assert view_model.trace_markdown == ""
    assert view_model.trace_visible is False
    assert view_model.csv_file_path is None
    assert view_model.json_file_path is None


def test_render_view_model_populates_result_chart_trace_and_exports() -> None:
    runtime = type(
        "Runtime",
        (),
        {"graph": object(), "session_repository": InMemorySessionRepository()},
    )()
    state = build_default_ui_state()
    state.update(
        {
            "status": "approved",
            "execution_result": {
                "row_count": 2,
                "columns": ["country", "users"],
                "rows": [
                    {"country": "UA", "users": 10},
                    {"country": "PL", "users": 5},
                ],
            },
            "chart_spec": {
                "type": "bar",
                "title": "Users by country",
                "x": ["UA", "PL"],
                "y": [10, 5],
            },
            "sql_generation_mode": "Few-shot fallback",
            "llm_status": "missing_api_key",
            "syntax_valid": True,
            "security_approved": True,
            "human_approved": True,
            "log_messages": ["Executed successfully"],
        }
    )

    view_model = _render_view_model(runtime, state)

    assert view_model.results_summary == "Rows returned: 2"
    assert list(view_model.result_table.columns) == ["country", "users"]
    assert view_model.result_table.iloc[0].to_dict() == {"country": "UA", "users": 10}
    assert isinstance(view_model.chart_figure, go.Figure)
    assert view_model.chart_figure.layout.title.text == "Users by country"
    assert "Execution trace" in view_model.trace_markdown
    assert "Executed successfully" in view_model.trace_markdown
    assert view_model.trace_visible is True
    assert view_model.csv_file_path is not None
    assert view_model.json_file_path is not None


def test_handle_apply_user_resets_active_conversation_state() -> None:
    runtime = build_gradio_runtime()
    state = build_default_ui_state()
    state.update(
        {
            "conversation_id": "conv-old",
            "selected_conversation_id": "conv-old",
            "pending_thread_id": "thread-old",
            "awaiting_edit_sql": True,
            "last_state": {"status": "pending"},
            "chat_messages": [{"role": "assistant", "content": "old"}],
        }
    )

    updated_state, view_model = handle_apply_user(runtime, state, "new-user", "New User")

    assert updated_state["user_id"] == "new-user"
    assert updated_state["display_name"] == "New User"
    assert updated_state["conversation_id"] != "conv-old"
    assert updated_state["pending_thread_id"] is None
    assert updated_state["chat_messages"] == []
    assert "Applied user profile." == view_model.status_message


def test_handle_send_question_waits_for_sql_approval() -> None:
    runtime = build_gradio_runtime()
    state = build_default_ui_state()
    state["user_id"] = "u-1"
    state["display_name"] = "User 1"

    def fake_start_query_turn(*_: object, **__: object) -> QueryTurnResult:
        return QueryTurnResult(
            thread_id="thread-test",
            awaiting_approval=True,
            state={
                "generated_sql": "SELECT COUNT(*) FROM users;",
                "llm_user_notice": "LLM fallback was used.",
                "sql_generation_mode": "Few-shot fallback",
                "llm_status": "missing_api_key",
                    "pending_thread_id": "thread-test",
                "status": "pending",
            },
        )

    from text_to_sql_agent.ui import gradio_app as gradio_module

    original_start_query_turn = gradio_module.start_query_turn
    gradio_module.start_query_turn = fake_start_query_turn

    try:
        updated_state, view_model = handle_send_question(runtime, state, "How many users?")
    finally:
        gradio_module.start_query_turn = original_start_query_turn

    assert updated_state["pending_thread_id"]
    assert updated_state["chat_messages"][0]["role"] == "user"
    assert "Proposed SQL query" in updated_state["chat_messages"][1]["content"]
    assert view_model.status_message == "Review the SQL before execution."
    assert view_model.sql_markdown
    assert view_model.approval_controls_visible is True


def test_handle_resume_with_decision_approve_returns_results() -> None:
    runtime = build_gradio_runtime()
    state = build_default_ui_state()
    state["user_id"] = "u-2"
    state["display_name"] = "User 2"

    pending_state, _ = handle_send_question(runtime, state, "How many users?")
    approved_state, view_model = handle_resume_with_decision(runtime, pending_state, "approve")

    assert approved_state["pending_thread_id"] is None
    assert approved_state["execution_result"] is not None
    assert view_model.results_summary.startswith("Rows returned:")
    assert view_model.chat_messages[-1]["content"].startswith("Rows returned:")
    assert view_model.approval_controls_visible is False


def test_handle_resume_with_decision_reject_returns_rejection_message() -> None:
    runtime = build_gradio_runtime()
    state = build_default_ui_state()
    state.update(
        {
            "conversation_id": "conv-reject-1",
            "pending_thread_id": "thread-reject-1",
            "generated_sql": "SELECT * FROM users;",
        }
    )

    from text_to_sql_agent.ui import gradio_app as gradio_module

    original_resume_query_turn = gradio_module.resume_query_turn

    def fake_resume_query_turn(*_: object, **__: object) -> dict[str, object]:
        return {
            "status": "rejected",
            "human_approved": False,
            "execution_result": None,
            "generated_sql": "SELECT * FROM users;",
            "pending_thread_id": None,
        }

    gradio_module.resume_query_turn = fake_resume_query_turn

    try:
        rejected_state, view_model = handle_resume_with_decision(runtime, state, "reject")
    finally:
        gradio_module.resume_query_turn = original_resume_query_turn

    assert rejected_state["pending_thread_id"] is None
    assert rejected_state["status"] == "rejected"
    assert view_model.results_summary == "SQL was rejected."
    assert view_model.chat_messages[-1]["content"] == "SQL was rejected."


def test_handle_submit_edited_sql_resumes_with_edit_payload() -> None:
    runtime = build_gradio_runtime()
    state = build_default_ui_state()
    state.update(
        {
            "conversation_id": "conv-edit-1",
            "pending_thread_id": "thread-edit-1",
            "generated_sql": "SELECT * FROM users;",
            "awaiting_edit_sql": True,
        }
    )

    captured: dict[str, object] = {}

    from text_to_sql_agent.ui import gradio_app as gradio_module

    original_resume_query_turn = gradio_module.resume_query_turn

    def fake_resume_query_turn(*_: object, **kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "status": "approved",
            "human_approved": True,
            "execution_result": {"row_count": 1, "columns": ["value"], "rows": [{"value": 1}]},
            "generated_sql": "SELECT value FROM users;",
            "pending_thread_id": None,
        }

    gradio_module.resume_query_turn = fake_resume_query_turn

    try:
        updated_state, view_model = gradio_module.handle_submit_edited_sql(
            runtime,
            state,
            "SELECT value FROM users;",
        )
    finally:
        gradio_module.resume_query_turn = original_resume_query_turn

    assert captured["conversation_id"] == "conv-edit-1"
    assert captured["thread_id"] == "thread-edit-1"
    assert captured["decision"] == {"edit": "SELECT value FROM users;"}
    assert updated_state["pending_thread_id"] is None
    assert updated_state["awaiting_edit_sql"] is False
    assert view_model.results_summary.startswith("Rows returned:")


def test_handle_load_selected_conversation_restores_history() -> None:
    runtime = build_gradio_runtime()
    state = build_default_ui_state()
    state["user_id"] = "u-3"
    state["display_name"] = "User 3"

    pending_state, _ = handle_send_question(runtime, state, "How many users?")
    loaded_state, view_model = handle_load_selected_conversation(
        runtime,
        handle_start_new_conversation(runtime, pending_state)[0],
        pending_state["conversation_id"],
    )

    assert loaded_state["conversation_id"] == pending_state["conversation_id"]
    assert loaded_state["chat_messages"]
    assert view_model.status_message.startswith("Opened conversation:")
