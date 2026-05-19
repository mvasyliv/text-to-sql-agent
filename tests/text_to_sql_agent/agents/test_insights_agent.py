"""Tests for insights agent (T-2026-05-18-050)."""

from text_to_sql_agent.agents import build_insights_node


def _execution_result() -> dict:
    return {
        "columns": ["country", "amount"],
        "rows": [{"country": "US", "amount": 10}, {"country": "DE", "amount": 5}],
        "row_count": 2,
    }


def test_build_insights_node_success():
    node = build_insights_node()
    result = node(
        {
            "execution_result": _execution_result(),
            "chart_spec": {"type": "bar", "x": ["US", "DE"], "y": [10, 5]},
        }
    )

    assert result["insight_text"] is not None
    assert "rows" in result["insight_text"]
    assert "narrative generated" in result["log_messages"][0]


def test_build_insights_node_missing_execution_result():
    node = build_insights_node()
    result = node({"chart_spec": {"type": "bar"}})

    assert result["insight_text"] is None
    assert result["status"] == "failed"
    assert "execution_result is missing" in result["error_message"]
