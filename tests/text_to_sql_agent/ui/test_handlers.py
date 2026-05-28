"""Tests for Chainlit UI handlers (T-2026-05-18-051)."""

from pathlib import Path

from text_to_sql_agent.ui.handlers import (
    build_export_files,
    build_ui_runtime,
    resume_query_turn,
    start_query_turn,
)


def test_start_query_turn_produces_sql_preview_and_waits_for_approval():
    runtime = build_ui_runtime()
    turn = start_query_turn(
        runtime,
        user_id="u-001",
        conversation_id="c-001",
        user_question="How many users?",
    )

    assert turn.awaiting_approval is True
    assert turn.state["generated_sql"] is not None
    assert turn.state["security_approved"] is True


def test_resume_query_turn_approve_reaches_done():
    runtime = build_ui_runtime()
    turn = start_query_turn(
        runtime,
        user_id="u-001",
        conversation_id="c-002",
        user_question="How many users?",
    )

    state = resume_query_turn(
        runtime,
        conversation_id="c-002",
        thread_id=turn.thread_id,
        decision="approve",
    )

    assert state["status"] == "done"
    assert state["execution_result"] is not None
    assert state["chart_spec"] is not None
    assert state["insight_text"]


def test_build_export_files_supports_multiple_formats(tmp_path: Path):
    state = {
        "execution_result": {
            "columns": ["id", "name"],
            "rows": [{"id": 1, "name": "Alice"}],
            "row_count": 1,
        }
    }

    result = build_export_files(state, formats=("csv", "json"), output_dir=tmp_path)

    assert set(result) == {"csv", "json"}
    assert Path(result["csv"]).exists()
    assert Path(result["json"]).exists()


def test_start_query_turn_propagates_selected_tables():
    runtime = build_ui_runtime()
    turn = start_query_turn(
        runtime,
        user_id="u-001",
        conversation_id="c-003",
        user_question="How many users?",
        selected_tables=["users"],
    )

    assert turn.state["selected_tables"] == ["users"]
