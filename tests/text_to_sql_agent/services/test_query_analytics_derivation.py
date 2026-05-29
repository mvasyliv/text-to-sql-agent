"""Tests for pure query analytics derivation helpers."""

import pytest

from text_to_sql_agent.services import (
    QueryAnalyticsChartDerivation,
    build_category_sum_derivation,
    build_frequency_derivation,
    build_numeric_line_derivation,
    build_row_count_fallback_derivation,
    derive_one_shot_chart,
    detect_categorical_columns,
    detect_numeric_columns,
    is_number,
)


def test_is_number_excludes_bools_and_accepts_numeric_scalars():
    assert is_number(10) is True
    assert is_number(3.5) is True
    assert is_number(True) is False
    assert is_number("10") is False


def test_detect_numeric_and_categorical_columns():
    rows = [
        {"country": "US", "amount": 10, "flag": True},
        {"country": "DE", "amount": 5, "flag": False},
    ]

    assert detect_numeric_columns(rows, ["country", "amount", "flag"]) == ("amount",)
    assert detect_categorical_columns(rows, ["country", "amount", "flag"]) == (
        "country",
        "flag",
    )


def test_build_category_sum_derivation_returns_sorted_chart():
    rows = [
        {"country": "US", "amount": 10},
        {"country": "US", "amount": 15},
        {"country": "DE", "amount": 5},
    ]

    derivation = build_category_sum_derivation(
        rows,
        category_column="country",
        value_column="amount",
        max_points=10,
    )

    assert isinstance(derivation, QueryAnalyticsChartDerivation)
    assert derivation.strategy == "category_sum"
    assert derivation.chart_spec["x"] == ["US", "DE"]
    assert derivation.chart_spec["y"] == [25.0, 5.0]
    assert derivation.primary_category_column == "country"
    assert derivation.primary_value_column == "amount"


def test_build_frequency_derivation_and_numeric_line_derivation():
    frequency = build_frequency_derivation(
        [{"status": "open"}, {"status": "closed"}, {"status": "open"}],
        category_column="status",
        max_points=10,
    )
    line = build_numeric_line_derivation(
        [{"metric": 1}, {"metric": 2}, {"metric": 3}],
        value_column="metric",
        max_points=10,
    )

    assert frequency.strategy == "categorical_count"
    assert frequency.chart_spec["y_title"] == "count"
    assert line.strategy == "numeric_line"
    assert line.chart_spec["type"] == "line"
    assert line.chart_spec["y"] == [1.0, 2.0, 3.0]


def test_build_row_count_fallback_derivation():
    derivation = build_row_count_fallback_derivation([{"a": 1}, {"a": 2}])

    assert derivation.strategy == "row_count_fallback"
    assert derivation.chart_spec["x"] == ["rows"]
    assert derivation.chart_spec["y"] == [2.0]
    assert derivation.insight_text == "Result contains 2 rows."


def test_derive_one_shot_chart_uses_empty_and_fallback_paths():
    empty = derive_one_shot_chart({"columns": ["a"], "rows": []})
    fallback = derive_one_shot_chart({"columns": ["a"], "rows": [{"a": None}, {"a": None}]})

    assert empty.strategy == "empty"
    assert empty.chart_spec["x"] == []
    assert fallback.strategy == "row_count_fallback"
    assert fallback.visible_point_count == 1


def test_derive_one_shot_chart_requires_rows_list_and_valid_max_points():
    with pytest.raises(ValueError):
        derive_one_shot_chart({"columns": ["a"]})

    with pytest.raises(ValueError):
        derive_one_shot_chart({"columns": ["a"], "rows": [{"a": 1}]}, max_points=0)

