"""Pure render-model builders for Chainlit UI content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SqlPreviewRenderModel:
    """Normalized SQL preview content."""

    sql: str
    content: str
    has_sql: bool


@dataclass(frozen=True, slots=True)
class ConversationActionLabelRenderModel:
    """Normalized label for a conversation action button."""

    title: str
    label: str
    fallback_label: str
    was_truncated: bool


@dataclass(frozen=True, slots=True)
class MarkdownTableRenderModel:
    """Normalized markdown table content for query results."""

    content: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    total_rows: int
    visible_row_count: int
    has_truncation: bool


@dataclass(frozen=True, slots=True)
class PlotlyFigureRenderModel:
    """Normalized Plotly figure payload."""

    chart_type: str
    trace_type: str | None
    is_line_chart: bool
    figure: dict[str, Any] | None


def build_sql_preview_render_model(sql_query: str) -> SqlPreviewRenderModel:
    """Build normalized SQL preview content from raw SQL text."""
    normalized = sql_query.strip()
    if not normalized:
        return SqlPreviewRenderModel(sql="", content="No SQL generated.", has_sql=False)

    return SqlPreviewRenderModel(
        sql=normalized,
        content=f"```sql\n{normalized}\n```",
        has_sql=True,
    )


def build_conversation_action_label_model(
    title: str | None,
    *,
    conversation_id: str,
    max_length: int = 48,
) -> ConversationActionLabelRenderModel:
    """Build a compact and stable conversation action label model."""
    fallback_label = f"Conversation {conversation_id[:8]}"
    normalized_title = (title or "").strip()
    label = normalized_title or fallback_label
    if max_length < 8:
        max_length = 8

    was_truncated = len(label) > max_length
    if was_truncated:
        label = label[: max_length - 3].rstrip() + "..."

    return ConversationActionLabelRenderModel(
        title=normalized_title,
        label=label,
        fallback_label=fallback_label,
        was_truncated=was_truncated,
    )


def build_markdown_table_render_model(
    execution_result: dict[str, Any],
    *,
    max_rows: int = 20,
) -> MarkdownTableRenderModel:
    """Build a normalized markdown table model from an execution result payload."""
    rows = execution_result.get("rows")
    if not isinstance(rows, list) or not rows:
        return MarkdownTableRenderModel(
            content="No rows returned.",
            columns=(),
            rows=(),
            total_rows=0,
            visible_row_count=0,
            has_truncation=False,
        )

    columns = execution_result.get("columns")
    if not isinstance(columns, list) or not columns:
        first_row = rows[0]
        if isinstance(first_row, dict):
            columns = list(first_row.keys())
        else:
            return MarkdownTableRenderModel(
                content="No tabular rows available.",
                columns=(),
                rows=(),
                total_rows=len(rows),
                visible_row_count=0,
                has_truncation=False,
            )

    visible_rows = rows[:max_rows]
    normalized_rows: list[tuple[str, ...]] = []
    for row in visible_rows:
        if not isinstance(row, dict):
            continue
        normalized_rows.append(tuple(str(row.get(col, "")) for col in columns))

    if not normalized_rows:
        return MarkdownTableRenderModel(
            content="No tabular rows available.",
            columns=tuple(str(col) for col in columns),
            rows=(),
            total_rows=len(rows),
            visible_row_count=0,
            has_truncation=False,
        )

    normalized_columns = tuple(str(col) for col in columns)
    header = "| " + " | ".join(normalized_columns) + " |"
    separator = "| " + " | ".join("---" for _ in normalized_columns) + " |"
    body_lines = ["| " + " | ".join(values) + " |" for values in normalized_rows]
    table = "\n".join([header, separator, *body_lines])
    has_truncation = len(rows) > max_rows
    if has_truncation:
        table += f"\n\nShowing first {max_rows} of {len(rows)} rows."

    return MarkdownTableRenderModel(
        content=table,
        columns=normalized_columns,
        rows=tuple(normalized_rows),
        total_rows=len(rows),
        visible_row_count=len(normalized_rows),
        has_truncation=has_truncation,
    )


def build_plotly_figure_model(chart_spec: dict[str, Any] | None) -> PlotlyFigureRenderModel:
    """Build a normalized Plotly figure model from an internal chart spec."""
    if not isinstance(chart_spec, dict):
        return PlotlyFigureRenderModel(
            chart_type="unknown",
            trace_type=None,
            is_line_chart=False,
            figure=None,
        )

    chart_type = str(chart_spec.get("type", "bar")).lower()
    x_values = chart_spec.get("x") or []
    y_values = chart_spec.get("y") or []

    is_line_chart = chart_type == "line"
    trace_type = "scatter" if is_line_chart else "bar"
    trace: dict[str, Any] = {
        "type": trace_type,
        "x": x_values,
        "y": y_values,
    }
    if is_line_chart:
        trace["mode"] = "lines+markers"

    figure = {
        "data": [trace],
        "layout": {
            "title": chart_spec.get("title") or "Query chart",
            "xaxis": {"title": chart_spec.get("x_title") or "x"},
            "yaxis": {"title": chart_spec.get("y_title") or "y"},
            "template": "plotly_white",
        },
    }

    return PlotlyFigureRenderModel(
        chart_type=chart_type,
        trace_type=trace_type,
        is_line_chart=is_line_chart,
        figure=figure,
    )

