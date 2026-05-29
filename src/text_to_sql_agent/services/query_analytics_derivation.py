"""Pure chart derivation helpers for one-shot query analytics."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Literal

ChartDerivationStrategy = Literal[
    "category_sum",
    "categorical_count",
    "numeric_line",
    "row_count_fallback",
    "empty",
]


@dataclass(frozen=True, slots=True)
class QueryAnalyticsChartDerivation:
    """Normalized chart derivation output for one-shot analytics."""

    chart_spec: dict[str, Any]
    insight_text: str
    strategy: ChartDerivationStrategy
    source_row_count: int
    visible_point_count: int
    primary_category_column: str | None = None
    primary_value_column: str | None = None


def is_number(value: Any) -> bool:
    """Return True when the value is a non-bool numeric scalar."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def detect_numeric_columns(rows: list[dict[str, Any]], columns: list[str]) -> tuple[str, ...]:
    """Return columns that contain only numeric, non-null values."""
    numeric: list[str] = []
    for column in columns:
        values = [row.get(column) for row in rows if row.get(column) is not None]
        if values and all(is_number(value) for value in values):
            numeric.append(column)
    return tuple(numeric)


def detect_categorical_columns(rows: list[dict[str, Any]], columns: list[str]) -> tuple[str, ...]:
    """Return columns that contain at least one non-numeric value."""
    categorical: list[str] = []
    for column in columns:
        values = [row.get(column) for row in rows if row.get(column) is not None]
        if values and any(not is_number(value) for value in values):
            categorical.append(column)
    return tuple(categorical)


def build_category_sum_derivation(
    rows: list[dict[str, Any]],
    *,
    category_column: str,
    value_column: str,
    max_points: int,
) -> QueryAnalyticsChartDerivation:
    """Build a bar-chart derivation by summing numeric values by category."""
    sums: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        category = str(row.get(category_column, "(null)"))
        value = row.get(value_column)
        if is_number(value):
            numeric_value = float(value)
            sums[category] += numeric_value

    pairs = sorted(sums.items(), key=lambda item: item[1], reverse=True)[:max_points]
    x = [item[0] for item in pairs]
    y = [item[1] for item in pairs]
    return QueryAnalyticsChartDerivation(
        chart_spec={
            "type": "bar",
            "x": x,
            "y": y,
            "x_title": category_column,
            "y_title": f"sum({value_column})",
        },
        insight_text=(
            f"Top {len(x)} {category_column} values by sum({value_column}) were prepared "
            f"from {len(rows)} rows."
        ),
        strategy="category_sum",
        source_row_count=len(rows),
        visible_point_count=len(x),
        primary_category_column=category_column,
        primary_value_column=value_column,
    )


def build_frequency_derivation(
    rows: list[dict[str, Any]],
    *,
    category_column: str,
    max_points: int,
) -> QueryAnalyticsChartDerivation:
    """Build a bar-chart derivation of category frequencies."""
    counts = Counter(str(row.get(category_column, "(null)")) for row in rows)
    pairs = counts.most_common(max_points)
    x = [item[0] for item in pairs]
    y = [float(item[1]) for item in pairs]
    return QueryAnalyticsChartDerivation(
        chart_spec={
            "type": "bar",
            "x": x,
            "y": y,
            "x_title": category_column,
            "y_title": "count",
        },
        insight_text=f"Frequency chart for {category_column} was prepared from {len(rows)} rows.",
        strategy="categorical_count",
        source_row_count=len(rows),
        visible_point_count=len(x),
        primary_category_column=category_column,
        primary_value_column="count",
    )


def build_numeric_line_derivation(
    rows: list[dict[str, Any]],
    *,
    value_column: str,
    max_points: int,
) -> QueryAnalyticsChartDerivation:
    """Build a line-chart derivation for numeric-only result sets."""
    values: list[float] = []
    for row in rows:
        value = row.get(value_column)
        if is_number(value):
            values.append(float(value))
    values = values[:max_points]
    x = [str(idx + 1) for idx in range(len(values))]
    return QueryAnalyticsChartDerivation(
        chart_spec={
            "type": "line",
            "x": x,
            "y": values,
            "x_title": "row_index",
            "y_title": value_column,
        },
        insight_text=f"Line chart for numeric column {value_column} was prepared from {len(values)} points.",
        strategy="numeric_line",
        source_row_count=len(rows),
        visible_point_count=len(values),
        primary_category_column="row_index",
        primary_value_column=value_column,
    )


def build_row_count_fallback_derivation(rows: list[dict[str, Any]]) -> QueryAnalyticsChartDerivation:
    """Build a fallback derivation when columns are present but not classifiable."""
    row_count = len(rows)
    return QueryAnalyticsChartDerivation(
        chart_spec={
            "type": "bar",
            "x": ["rows"],
            "y": [float(row_count)],
            "x_title": "metric",
            "y_title": "value",
        },
        insight_text=f"Result contains {row_count} rows.",
        strategy="row_count_fallback",
        source_row_count=row_count,
        visible_point_count=1,
        primary_category_column="metric",
        primary_value_column="value",
    )


def derive_one_shot_chart(
    execution_result: dict[str, Any],
    *,
    max_points: int = 20,
) -> QueryAnalyticsChartDerivation:
    """Derive a single chart spec and summary from an execution result payload."""
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
        return QueryAnalyticsChartDerivation(
            chart_spec={
                "type": "bar",
                "x": [],
                "y": [],
                "x_title": "category",
                "y_title": "value",
            },
            insight_text="No rows returned by the query.",
            strategy="empty",
            source_row_count=0,
            visible_point_count=0,
        )

    numeric_columns = detect_numeric_columns(rows, columns)
    categorical_columns = detect_categorical_columns(rows, columns)

    if categorical_columns and numeric_columns:
        return build_category_sum_derivation(
            rows,
            category_column=categorical_columns[0],
            value_column=numeric_columns[0],
            max_points=max_points,
        )

    if categorical_columns:
        return build_frequency_derivation(
            rows,
            category_column=categorical_columns[0],
            max_points=max_points,
        )

    if numeric_columns:
        return build_numeric_line_derivation(
            rows,
            value_column=numeric_columns[0],
            max_points=max_points,
        )

    return build_row_count_fallback_derivation(rows)

