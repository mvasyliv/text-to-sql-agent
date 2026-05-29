"""Pure transformation helpers for query insight generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class QueryInsightDerivation:
    """Normalized output of the query insight transformation pipeline."""

    text: str
    row_count: int
    column_count: int
    chart_type: str | None
    plotted_points: int
    has_chart_metadata: bool
    has_rows: bool


def safe_list_length(value: Any) -> int:
    """Return the length of a list value or zero for unsupported inputs."""
    return len(value) if isinstance(value, list) else 0


def build_no_rows_insight() -> QueryInsightDerivation:
    """Build the deterministic insight for an empty result set."""
    return QueryInsightDerivation(
        text="The query returned no rows.",
        row_count=0,
        column_count=0,
        chart_type=None,
        plotted_points=0,
        has_chart_metadata=False,
        has_rows=False,
    )


def build_query_insight_derivation(
    execution_result: dict[str, Any],
    chart_spec: dict[str, Any] | None,
) -> QueryInsightDerivation:
    """Derive a stable insight payload from query execution output."""
    rows = execution_result.get("rows")
    columns = execution_result.get("columns")
    row_count = execution_result.get("row_count")

    if not isinstance(rows, list):
        raise ValueError("execution_result must contain list field 'rows'")

    effective_row_count = row_count if isinstance(row_count, int) else len(rows)
    column_count = safe_list_length(columns)

    if effective_row_count == 0:
        return build_no_rows_insight()

    chart_type = None
    x_count = 0
    y_count = 0
    has_chart_metadata = isinstance(chart_spec, dict)
    if has_chart_metadata:
        chart_type = chart_spec.get("type")
        x_count = safe_list_length(chart_spec.get("x"))
        y_count = safe_list_length(chart_spec.get("y"))

    if chart_type:
        text = (
            f"The query returned {effective_row_count} rows across {column_count} columns. "
            f"A {chart_type} chart was generated with {max(x_count, y_count)} plotted points."
        )
    else:
        text = (
            f"The query returned {effective_row_count} rows across {column_count} columns. "
            "No chart metadata was available for additional insight."
        )

    return QueryInsightDerivation(
        text=text,
        row_count=effective_row_count,
        column_count=column_count,
        chart_type=str(chart_type) if chart_type else None,
        plotted_points=max(x_count, y_count),
        has_chart_metadata=has_chart_metadata,
        has_rows=True,
    )

