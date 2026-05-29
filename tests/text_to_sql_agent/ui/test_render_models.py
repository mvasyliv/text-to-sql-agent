"""Tests for pure UI render-model builders."""

from text_to_sql_agent.ui.render_models import (
    build_conversation_action_label_model,
    build_markdown_table_render_model,
    build_plotly_figure_model,
    build_sql_preview_render_model,
)


def test_build_sql_preview_render_model_normalizes_sql_text():
    model = build_sql_preview_render_model("  SELECT id FROM users  ")

    assert model.has_sql is True
    assert model.sql == "SELECT id FROM users"
    assert model.content == "```sql\nSELECT id FROM users\n```"


def test_build_sql_preview_render_model_handles_empty_sql():
    model = build_sql_preview_render_model("   ")

    assert model.has_sql is False
    assert model.sql == ""
    assert model.content == "No SQL generated."


def test_build_conversation_action_label_model_uses_fallback_and_truncation():
    fallback_model = build_conversation_action_label_model(
        "   ",
        conversation_id="conv-1234abcd",
    )
    truncated_model = build_conversation_action_label_model(
        "Very long conversation title that should be truncated safely",
        conversation_id="conv-1234abcd",
        max_length=18,
    )

    assert fallback_model.label == "Conversation conv-123"
    assert fallback_model.fallback_label == "Conversation conv-123"
    assert fallback_model.was_truncated is False
    assert truncated_model.label == "Very long conve..."
    assert truncated_model.was_truncated is True


def test_build_markdown_table_render_model_reports_truncation_and_content():
    model = build_markdown_table_render_model(
        {
            "columns": ["id", "name"],
            "rows": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Cara"},
            ],
        },
        max_rows=2,
    )

    assert model.columns == ("id", "name")
    assert model.rows == (("1", "Alice"), ("2", "Bob"))
    assert model.total_rows == 3
    assert model.visible_row_count == 2
    assert model.has_truncation is True
    assert "Showing first 2 of 3 rows." in model.content


def test_build_markdown_table_render_model_handles_missing_rows():
    model = build_markdown_table_render_model({"rows": []})

    assert model.content == "No rows returned."
    assert model.columns == ()
    assert model.rows == ()
    assert model.total_rows == 0


def test_build_plotly_figure_model_builds_line_and_fallback_payloads():
    line_model = build_plotly_figure_model(
        {
            "type": "line",
            "x": ["1", "2"],
            "y": [10, 12],
            "x_title": "row_index",
            "y_title": "amount",
        }
    )
    fallback_model = build_plotly_figure_model(None)

    assert line_model.chart_type == "line"
    assert line_model.trace_type == "scatter"
    assert line_model.is_line_chart is True
    assert line_model.figure is not None
    assert line_model.figure["data"][0]["mode"] == "lines+markers"
    assert fallback_model.figure is None

