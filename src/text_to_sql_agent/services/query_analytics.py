"""Lightweight analytics over executed query results."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class QueryAnalyticsResult:
    """One-shot chart and text summary for a tabular result set."""

    chart_spec: dict[str, Any]
    insight_text: str


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _detect_numeric_columns(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    numeric: list[str] = []
    for col in columns:
        values = [row.get(col) for row in rows if row.get(col) is not None]
        if values and all(_is_number(value) for value in values):
            numeric.append(col)
    return numeric


def _detect_categorical_columns(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    categorical: list[str] = []
    for col in columns:
        values = [row.get(col) for row in rows if row.get(col) is not None]
        if values and any(not _is_number(value) for value in values):
            categorical.append(col)
    return categorical


def _truncate_pairs(pairs: list[tuple[str, float]], max_points: int) -> list[tuple[str, float]]:
    return pairs[:max_points]


def build_one_shot_chart(
    execution_result: dict[str, Any],
    *,
    max_points: int = 20,
) -> QueryAnalyticsResult:
    """Build one chart spec and concise insight from execution result."""
    rows = execution_result.get("rows")
    if not isinstance(rows, list):
        raise ValueError("execution_result must contain list field 'rows'")

    if max_points <= 0:
        raise ValueError("max_points must be greater than zero")

    columns = execution_result.get("columns")
    if not isinstance(columns, list):
        if rows and isinstance(rows[0], dict):
            columns = list(rows[0].keys())
        else:
            columns = []

    if not rows:
        return QueryAnalyticsResult(
            chart_spec={
                "type": "bar",
                "x": [],
                "y": [],
                "x_title": "category",
                "y_title": "value",
            },
            insight_text="No rows returned by the query.",
        )

    numeric_cols = _detect_numeric_columns(rows, columns)
    categorical_cols = _detect_categorical_columns(rows, columns)

    if categorical_cols and numeric_cols:
        category_col = categorical_cols[0]
        value_col = numeric_cols[0]
        sums: defaultdict[str, float] = defaultdict(float)
        for row in rows:
            category = str(row.get(category_col, "(null)"))
            value = row.get(value_col)
            if _is_number(value):
                sums[category] += float(value)
        pairs = sorted(sums.items(), key=lambda item: item[1], reverse=True)
        pairs = _truncate_pairs(pairs, max_points)
        x = [item[0] for item in pairs]
        y = [item[1] for item in pairs]
        return QueryAnalyticsResult(
            chart_spec={
                "type": "bar",
                "x": x,
                "y": y,
                "x_title": category_col,
                "y_title": f"sum({value_col})",
            },
            insight_text=(
                f"Top {len(x)} {category_col} values by sum({value_col}) were prepared "
                f"from {len(rows)} rows."
            ),
        )

    if categorical_cols:
        category_col = categorical_cols[0]
        counts = Counter(str(row.get(category_col, "(null)")) for row in rows)
        pairs = counts.most_common(max_points)
        x = [item[0] for item in pairs]
        y = [float(item[1]) for item in pairs]
        return QueryAnalyticsResult(
            chart_spec={
                "type": "bar",
                "x": x,
                "y": y,
                "x_title": category_col,
                "y_title": "count",
            },
            insight_text=(
                f"Frequency chart for {category_col} was prepared from {len(rows)} rows."
            ),
        )

    if numeric_cols:
        value_col = numeric_cols[0]
        values = [float(row.get(value_col)) for row in rows if _is_number(row.get(value_col))]
        values = values[:max_points]
        x = [str(idx + 1) for idx in range(len(values))]
        return QueryAnalyticsResult(
            chart_spec={
                "type": "line",
                "x": x,
                "y": values,
                "x_title": "row_index",
                "y_title": value_col,
            },
            insight_text=(
                f"Line chart for numeric column {value_col} was prepared from {len(values)} points."
            ),
        )

    # Fallback when columns are present but cannot be categorized.
    return QueryAnalyticsResult(
        chart_spec={
            "type": "bar",
            "x": ["rows"],
            "y": [float(len(rows))],
            "x_title": "metric",
            "y_title": "value",
        },
        insight_text=f"Result contains {len(rows)} rows.",
    )
