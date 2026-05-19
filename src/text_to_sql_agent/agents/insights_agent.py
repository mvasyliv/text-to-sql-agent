"""Insights agent over already executed query results."""

from __future__ import annotations

from text_to_sql_agent.services import build_query_insight


def build_insights_node():
    """Return a LangGraph-compatible insights node."""

    def node(state: dict) -> dict:
        execution_result = state.get("execution_result")
        if not isinstance(execution_result, dict):
            return {
                "insight_text": None,
                "status": "failed",
                "error_message": "insights: execution_result is missing",
                "log_messages": ["insights: ERROR - execution_result is missing"],
            }

        chart_spec = state.get("chart_spec")
        try:
            insight = build_query_insight(execution_result, chart_spec)
            return {
                "insight_text": insight.text,
                "log_messages": ["insights: narrative generated"],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "insight_text": None,
                "status": "failed",
                "error_message": f"insights: failed - {exc}",
                "log_messages": [f"insights: ERROR - {exc}"],
            }

    return node
