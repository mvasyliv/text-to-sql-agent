"""Chainlit UI integration for the text-to-SQL workflow."""

__version__ = "0.1.0"

from .auth_callbacks import (
    authenticate_with_password,
    build_auth_service_from_env,
    make_chainlit_user,
)
from .handlers import (
    QueryTurnResult,
    UiRuntime,
    build_export_files,
    build_ui_runtime,
    resume_query_turn,
    start_query_turn,
)
from .renderers import (
    build_plotly_figure,
    render_conversation_action_label,
    render_markdown_table,
    render_sql_preview,
)

__all__ = [
    "authenticate_with_password",
    "build_auth_service_from_env",
    "make_chainlit_user",
    "QueryTurnResult",
    "UiRuntime",
    "build_export_files",
    "build_plotly_figure",
    "build_ui_runtime",
    "render_conversation_action_label",
    "render_markdown_table",
    "render_sql_preview",
    "resume_query_turn",
    "start_query_turn",
]
