"""Lightweight analytics over executed query results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .query_analytics_derivation import (
    QueryAnalyticsChartDerivation,
    derive_one_shot_chart,
)


@dataclass(frozen=True, slots=True)
class QueryAnalyticsResult:
    """One-shot chart and text summary for a tabular result set."""

    chart_spec: dict[str, Any]
    insight_text: str


def build_one_shot_chart(
    execution_result: dict[str, Any],
    *,
    max_points: int = 20,
) -> QueryAnalyticsResult:
    """Build one chart spec and concise insight from execution result."""
    derivation: QueryAnalyticsChartDerivation = derive_one_shot_chart(
        execution_result,
        max_points=max_points,
    )
    return QueryAnalyticsResult(
        chart_spec=derivation.chart_spec,
        insight_text=derivation.insight_text,
    )
