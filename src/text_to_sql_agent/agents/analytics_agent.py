"""Analytics agent for one-shot chart generation from execution results."""

from __future__ import annotations

from text_to_sql_agent.services import build_one_shot_chart


def build_analytics_node(*, max_points: int = 20):
    """Return a LangGraph-compatible analytics node."""

    def node(state: dict) -> dict:
        execution_result = state.get("execution_result")
        if not isinstance(execution_result, dict):
            return {
                "chart_spec": None,
                "insight_text": None,
                "status": "failed",
                "error_message": "analytics: execution_result is missing",
                "log_messages": ["analytics: ERROR - execution_result is missing"],
            }

        try:
            result = build_one_shot_chart(execution_result, max_points=max_points)
            return {
                "chart_spec": result.chart_spec,
                "insight_text": result.insight_text,
                "log_messages": ["analytics: chart spec produced"],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "chart_spec": None,
                "insight_text": None,
                "status": "failed",
                "error_message": f"analytics: failed - {exc}",
                "log_messages": [f"analytics: ERROR - {exc}"],
            }

    return node
