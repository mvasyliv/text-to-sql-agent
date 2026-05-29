"""Generate concise insights from executed query results and chart spec."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .query_insights_derivation import build_query_insight_derivation


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
    derivation = build_query_insight_derivation(execution_result, chart_spec)
    return QueryInsightResult(text=derivation.text)
