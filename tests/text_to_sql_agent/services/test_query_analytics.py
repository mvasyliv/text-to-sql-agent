"""Tests for one-shot query analytics service (T-2026-05-18-049)."""

import pytest

from text_to_sql_agent.services import QueryAnalyticsResult, build_one_shot_chart


def test_build_one_shot_chart_with_category_and_numeric_sum():
    execution_result = {
        "columns": ["country", "amount"],
        "rows": [
            {"country": "US", "amount": 10},
            {"country": "US", "amount": 15},
            {"country": "DE", "amount": 5},
        ],
    }

    result = build_one_shot_chart(execution_result)
    assert isinstance(result, QueryAnalyticsResult)
    assert result.chart_spec["type"] == "bar"
    assert result.chart_spec["x_title"] == "country"
    assert result.chart_spec["y_title"] == "sum(amount)"
    assert result.chart_spec["x"][0] == "US"
    assert result.chart_spec["y"][0] == 25.0


def test_build_one_shot_chart_with_categorical_counts():
    execution_result = {
        "columns": ["status"],
        "rows": [
            {"status": "open"},
            {"status": "closed"},
            {"status": "open"},
        ],
    }

    result = build_one_shot_chart(execution_result)
    assert result.chart_spec["type"] == "bar"
    assert result.chart_spec["y_title"] == "count"
    assert "open" in result.chart_spec["x"]


def test_build_one_shot_chart_with_numeric_line():
    execution_result = {
        "columns": ["metric"],
        "rows": [{"metric": 1}, {"metric": 2}, {"metric": 3}],
    }

    result = build_one_shot_chart(execution_result)
    assert result.chart_spec["type"] == "line"
    assert result.chart_spec["y"] == [1.0, 2.0, 3.0]


def test_build_one_shot_chart_empty_rows():
    result = build_one_shot_chart({"columns": ["a"], "rows": []})
    assert result.chart_spec["x"] == []
    assert "No rows" in result.insight_text


def test_build_one_shot_chart_requires_rows_list():
    with pytest.raises(ValueError):
        build_one_shot_chart({"columns": ["a"]})


def test_build_one_shot_chart_invalid_max_points():
    with pytest.raises(ValueError):
        build_one_shot_chart({"columns": ["a"], "rows": [{"a": 1}]}, max_points=0)
