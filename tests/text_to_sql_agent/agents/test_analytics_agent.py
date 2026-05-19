"""Tests for analytics agent (T-2026-05-18-049)."""

from text_to_sql_agent.agents import build_analytics_node


def _execution_result() -> dict:
    return {
        "columns": ["country", "amount"],
        "rows": [
            {"country": "US", "amount": 10},
            {"country": "DE", "amount": 5},
            {"country": "US", "amount": 15},
        ],
    }


def test_build_analytics_node_success():
    node = build_analytics_node(max_points=10)
    result = node({"execution_result": _execution_result()})

    assert result["chart_spec"] is not None
    assert result["chart_spec"]["type"] in {"bar", "line"}
    assert result["insight_text"]
    assert "produced" in result["log_messages"][0]


def test_build_analytics_node_missing_execution_result():
    node = build_analytics_node()
    result = node({})

    assert result["chart_spec"] is None
    assert result["status"] == "failed"
    assert "execution_result is missing" in result["error_message"]


def test_build_analytics_node_handles_failure():
    node = build_analytics_node(max_points=0)
    result = node({"execution_result": _execution_result()})

    assert result["chart_spec"] is None
    assert result["status"] == "failed"
    assert "max_points" in result["error_message"]
