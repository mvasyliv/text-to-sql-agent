"""UI orchestration helpers for Chainlit flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from langgraph.types import Command

from text_to_sql_agent.graphs import build_query_graph
from text_to_sql_agent.models.session import ChatMessage, Conversation, MessageRole, User
from text_to_sql_agent.repositories.session_repository import InMemorySessionRepository, SessionRepository
from text_to_sql_agent.services import export_query_result


@dataclass(frozen=True, slots=True)
class QueryTurnResult:
    """Result of one user turn processed through the query graph."""

    thread_id: str
    state: dict[str, Any]
    awaiting_approval: bool


@dataclass(slots=True)
class UiRuntime:
    """Runtime dependencies required by the UI layer."""

    graph: Any
    session_repository: SessionRepository
    database_id: str = "default"
    dialect: str = "sqlite"


def build_ui_runtime(
    *,
    connection_config: dict[str, Any] | None = None,
    session_repository: SessionRepository | None = None,
    database_id: str = "default",
    dialect: str = "sqlite",
) -> UiRuntime:
    """Build runtime dependencies for Chainlit UI."""
    graph = build_query_graph(connection_config=connection_config)
    repository = session_repository or InMemorySessionRepository()
    return UiRuntime(
        graph=graph,
        session_repository=repository,
        database_id=database_id,
        dialect=dialect,
    )


def start_query_turn(
    runtime: UiRuntime,
    *,
    user_id: str,
    conversation_id: str,
    user_question: str,
    selected_tables: list[str] | None = None,
    thread_id: str | None = None,
) -> QueryTurnResult:
    """Start a new graph turn and return intermediate state."""
    _ensure_user_and_conversation(
        runtime.session_repository,
        user_id=user_id,
        conversation_id=conversation_id,
        title=user_question,
    )
    _append_message(
        runtime.session_repository,
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=user_question,
    )

    resolved_thread_id = thread_id or f"thread-{uuid4().hex}"
    state = _initial_query_state(
        user_id=user_id,
        conversation_id=conversation_id,
        user_question=user_question,
        database_id=runtime.database_id,
        dialect=runtime.dialect,
        selected_tables=selected_tables,
    )
    result = runtime.graph.invoke(
        state,
        {"configurable": {"thread_id": resolved_thread_id}},
    )

    sql_preview = str(result.get("generated_sql") or "")
    if sql_preview:
        _append_message(
            runtime.session_repository,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=sql_preview,
            metadata={"kind": "sql_preview"},
        )

    awaiting_approval = bool(sql_preview) and result.get("human_approved") is None
    return QueryTurnResult(
        thread_id=resolved_thread_id,
        state=result,
        awaiting_approval=awaiting_approval,
    )


def resume_query_turn(
    runtime: UiRuntime,
    *,
    conversation_id: str,
    thread_id: str,
    decision: str | dict[str, str],
) -> dict[str, Any]:
    """Resume paused graph from the human approval checkpoint."""
    result = runtime.graph.invoke(
        Command(resume=decision),
        {"configurable": {"thread_id": thread_id}},
    )

    _append_message(
        runtime.session_repository,
        conversation_id=conversation_id,
        role=MessageRole.TOOL,
        content=str(result.get("status", "done")),
        metadata={
            "kind": "approval_result",
            "human_approved": str(result.get("human_approved")),
            "row_count": str((result.get("execution_result") or {}).get("row_count", 0)),
        },
    )
    return result


def build_export_files(
    state: dict[str, Any],
    *,
    formats: tuple[str, ...] = ("csv", "json"),
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    """Export execution result to one or many formats."""
    execution_result = state.get("execution_result")
    if not isinstance(execution_result, dict):
        raise ValueError("execution_result is required for export")

    exported: dict[str, str] = {}
    for export_format in formats:
        exported[export_format] = export_query_result(
            execution_result,
            export_format=export_format,
            output_dir=output_dir,
        )
    return exported


def _initial_query_state(
    *,
    user_id: str,
    conversation_id: str,
    user_question: str,
    database_id: str,
    dialect: str,
    selected_tables: list[str] | None,
) -> dict[str, Any]:
    message_id = f"msg-{uuid4().hex}"
    return {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "user_question": user_question,
        "database_id": database_id,
        "dialect": dialect,
        "selected_tables": selected_tables,
        "schema_context": None,
        "generated_sql": None,
        "sql_generation_prompt": None,
        "sql_generation_mode": None,
        "sql_rationale": None,
        "llm_status": None,
        "llm_user_notice": None,
        "syntax_valid": None,
        "syntax_errors": [],
        "security_approved": None,
        "security_violations": [],
        "human_approved": None,
        "edited_sql": None,
        "execution_result": None,
        "execution_error": None,
        "chart_spec": None,
        "export_path": None,
        "insight_text": None,
        "status": "pending",
        "error_message": None,
        "log_messages": [],
    }


def _ensure_user_and_conversation(
    repository: SessionRepository,
    *,
    user_id: str,
    conversation_id: str,
    title: str,
) -> None:
    if repository.get_user(user_id) is None:
        repository.save_user(User(user_id=user_id, display_name=user_id))

    if repository.get_conversation(conversation_id) is None:
        repository.save_conversation(
            Conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                title=title.strip()[:80] or "DB assistant conversation",
                metadata={"source": "chainlit"},
            )
        )


def _append_message(
    repository: SessionRepository,
    *,
    conversation_id: str,
    role: MessageRole,
    content: str,
    metadata: dict[str, str] | None = None,
) -> None:
    repository.append_message(
        ChatMessage(
            message_id=f"msg-{uuid4().hex}",
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
    )
