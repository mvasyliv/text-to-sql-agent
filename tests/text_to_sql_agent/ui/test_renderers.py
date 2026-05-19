"""Tests for UI render helpers (T-2026-05-18-051)."""

from text_to_sql_agent.ui.renderers import (
    build_plotly_figure,
    render_markdown_table,
    render_sql_preview,
)


def test_render_sql_preview_wraps_query_in_sql_fence():
    rendered = render_sql_preview("SELECT id FROM users")
    assert rendered.startswith("```sql")
    assert "SELECT id FROM users" in rendered


def test_render_markdown_table_outputs_rows_and_columns():
    rendered = render_markdown_table(
        {
            "columns": ["id", "name"],
            "rows": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ],
        }
    )

    assert "| id | name |" in rendered
    assert "| 1 | Alice |" in rendered
    assert "| 2 | Bob |" in rendered


def test_build_plotly_figure_for_line_chart():
    figure = build_plotly_figure(
        {
            "type": "line",
            "x": ["1", "2"],
            "y": [10, 12],
            "x_title": "row_index",
            "y_title": "amount",
        }
    )

    assert figure is not None
    assert figure["data"][0]["type"] == "scatter"
    assert figure["data"][0]["mode"] == "lines+markers"
    assert figure["layout"]["xaxis"]["title"] == "row_index"
