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
from .render_models import (
    ConversationActionLabelRenderModel,
    MarkdownTableRenderModel,
    PlotlyFigureRenderModel,
    SqlPreviewRenderModel,
    build_conversation_action_label_model,
    build_markdown_table_render_model,
    build_plotly_figure_model,
    build_sql_preview_render_model,
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
    "build_conversation_action_label_model",
    "build_markdown_table_render_model",
    "build_plotly_figure",
    "build_plotly_figure_model",
    "build_ui_runtime",
    "build_sql_preview_render_model",
    "ConversationActionLabelRenderModel",
    "MarkdownTableRenderModel",
    "PlotlyFigureRenderModel",
    "SqlPreviewRenderModel",
    "render_conversation_action_label",
    "render_markdown_table",
    "render_sql_preview",
    "resume_query_turn",
    "start_query_turn",
]
