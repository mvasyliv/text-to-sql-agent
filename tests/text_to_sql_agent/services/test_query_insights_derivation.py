"""Tests for pure query insight derivation helpers."""

import pytest

from text_to_sql_agent.services import (
    QueryInsightDerivation,
    build_no_rows_insight,
    build_query_insight_derivation,
    safe_list_length,
)


def test_safe_list_length_handles_lists_only():
    assert safe_list_length([1, 2, 3]) == 3
    assert safe_list_length((1, 2, 3)) == 0
    assert safe_list_length(None) == 0


def test_build_no_rows_insight_returns_empty_derivation():
    derivation = build_no_rows_insight()

    assert isinstance(derivation, QueryInsightDerivation)
    assert derivation.text == "The query returned no rows."
    assert derivation.row_count == 0
    assert derivation.has_rows is False
    assert derivation.has_chart_metadata is False


def test_build_query_insight_derivation_with_chart_metadata():
    execution_result = {
        "columns": ["country", "amount"],
        "rows": [{"country": "US", "amount": 10}, {"country": "DE", "amount": 5}],
        "row_count": 2,
    }
    chart_spec = {"type": "bar", "x": ["US", "DE"], "y": [10, 5]}

    derivation = build_query_insight_derivation(execution_result, chart_spec)

    assert derivation.row_count == 2
    assert derivation.column_count == 2
    assert derivation.chart_type == "bar"
    assert derivation.plotted_points == 2
    assert derivation.has_chart_metadata is True
    assert "2 rows" in derivation.text
    assert "bar chart" in derivation.text


def test_build_query_insight_derivation_without_chart_metadata():
    execution_result = {
        "columns": ["id"],
        "rows": [{"id": 1}],
        "row_count": 1,
    }

    derivation = build_query_insight_derivation(execution_result, None)

    assert derivation.chart_type is None
    assert derivation.has_chart_metadata is False
    assert "No chart metadata" in derivation.text


def test_build_query_insight_derivation_empty_rows():
    execution_result = {
        "columns": ["id"],
        "rows": [],
        "row_count": 0,
    }

    derivation = build_query_insight_derivation(execution_result, {"type": "bar"})

    assert derivation.text == "The query returned no rows."
    assert derivation.has_rows is False


def test_build_query_insight_derivation_requires_rows_list():
    with pytest.raises(ValueError):
        build_query_insight_derivation({"columns": ["id"]}, {"type": "bar"})

