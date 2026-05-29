"""Rendering helpers for SQL preview, table output, and chart specs."""

from __future__ import annotations

from typing import Any

from .render_models import (
    build_conversation_action_label_model,
    build_markdown_table_render_model,
    build_plotly_figure_model,
    build_sql_preview_render_model,
)


def render_sql_preview(sql_query: str) -> str:
    """Return markdown SQL preview block."""
    return build_sql_preview_render_model(sql_query).content


def render_conversation_action_label(
    title: str | None,
    *,
    conversation_id: str,
    max_length: int = 48,
) -> str:
    """Return a compact action label for one conversation entry."""
    return build_conversation_action_label_model(
        title,
        conversation_id=conversation_id,
        max_length=max_length,
    ).label


def render_markdown_table(execution_result: dict[str, Any], *, max_rows: int = 20) -> str:
    """Return markdown table for execution result."""
    return build_markdown_table_render_model(execution_result, max_rows=max_rows).content


def build_plotly_figure(chart_spec: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert internal chart spec to a Plotly-compatible figure dict."""
    return build_plotly_figure_model(chart_spec).figure
