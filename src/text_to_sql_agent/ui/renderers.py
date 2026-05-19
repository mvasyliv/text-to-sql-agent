"""Rendering helpers for SQL preview, table output, and chart specs."""

from __future__ import annotations

from typing import Any


def render_sql_preview(sql_query: str) -> str:
    """Return markdown SQL preview block."""
    normalized = sql_query.strip()
    if not normalized:
        return "No SQL generated."
    return f"```sql\n{normalized}\n```"


def render_markdown_table(execution_result: dict[str, Any], *, max_rows: int = 20) -> str:
    """Return markdown table for execution result."""
    rows = execution_result.get("rows")
    if not isinstance(rows, list) or not rows:
        return "No rows returned."

    columns = execution_result.get("columns")
    if not isinstance(columns, list) or not columns:
        first_row = rows[0]
        if isinstance(first_row, dict):
            columns = list(first_row.keys())
        else:
            return "No tabular rows available."

    visible_rows = rows[:max_rows]
    header = "| " + " | ".join(str(col) for col in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"

    body_lines: list[str] = []
    for row in visible_rows:
        if not isinstance(row, dict):
            continue
        values = [str(row.get(col, "")) for col in columns]
        body_lines.append("| " + " | ".join(values) + " |")

    if not body_lines:
        return "No tabular rows available."

    table = "\n".join([header, separator, *body_lines])
    if len(rows) > max_rows:
        table += f"\n\nShowing first {max_rows} of {len(rows)} rows."
    return table


def build_plotly_figure(chart_spec: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert internal chart spec to a Plotly-compatible figure dict."""
    if not isinstance(chart_spec, dict):
        return None

    chart_type = str(chart_spec.get("type", "bar")).lower()
    x_values = chart_spec.get("x") or []
    y_values = chart_spec.get("y") or []

    trace_type = "bar" if chart_type != "line" else "scatter"
    mode = "lines+markers" if chart_type == "line" else None

    trace: dict[str, Any] = {
        "type": trace_type,
        "x": x_values,
        "y": y_values,
    }
    if mode:
        trace["mode"] = mode

    return {
        "data": [trace],
        "layout": {
            "title": chart_spec.get("title") or "Query chart",
            "xaxis": {"title": chart_spec.get("x_title") or "x"},
            "yaxis": {"title": chart_spec.get("y_title") or "y"},
            "template": "plotly_white",
        },
    }
