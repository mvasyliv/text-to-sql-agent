"""Generate concise insights from executed query results and chart spec."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class QueryInsightResult:
    """Compact insight payload returned by the insights service."""

    text: str


def _safe_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def build_query_insight(
    execution_result: dict[str, Any],
    chart_spec: dict[str, Any] | None,
) -> QueryInsightResult:
    """Build concise insight text from result rows and chart metadata.

    The service is deterministic and does not access the database.
    """
    rows = execution_result.get("rows")
    columns = execution_result.get("columns")
    row_count = execution_result.get("row_count")

    if not isinstance(rows, list):
        raise ValueError("execution_result must contain list field 'rows'")

    effective_row_count = row_count if isinstance(row_count, int) else len(rows)
    column_count = _safe_len(columns)

    if effective_row_count == 0:
        return QueryInsightResult(text="The query returned no rows.")

    chart_type = None
    x_count = 0
    y_count = 0
    if isinstance(chart_spec, dict):
        chart_type = chart_spec.get("type")
        x_count = _safe_len(chart_spec.get("x"))
        y_count = _safe_len(chart_spec.get("y"))

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

    return QueryInsightResult(text=text)
