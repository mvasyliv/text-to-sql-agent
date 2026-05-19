"""Tests for query insights service (T-2026-05-18-050)."""

import pytest

from text_to_sql_agent.services import QueryInsightResult, build_query_insight


def test_build_query_insight_with_chart_metadata():
    execution_result = {
        "columns": ["country", "amount"],
        "rows": [{"country": "US", "amount": 10}, {"country": "DE", "amount": 5}],
        "row_count": 2,
    }
    chart_spec = {"type": "bar", "x": ["US", "DE"], "y": [10, 5]}

    result = build_query_insight(execution_result, chart_spec)
    assert isinstance(result, QueryInsightResult)
    assert "2 rows" in result.text
    assert "bar chart" in result.text


def test_build_query_insight_without_chart_metadata():
    execution_result = {
        "columns": ["id"],
        "rows": [{"id": 1}],
        "row_count": 1,
    }

    result = build_query_insight(execution_result, None)
    assert "No chart metadata" in result.text


def test_build_query_insight_empty_rows():
    execution_result = {
        "columns": ["id"],
        "rows": [],
        "row_count": 0,
    }

    result = build_query_insight(execution_result, {"type": "bar"})
    assert result.text == "The query returned no rows."


def test_build_query_insight_requires_rows_list():
    with pytest.raises(ValueError):
        build_query_insight({"columns": ["id"]}, {"type": "bar"})
