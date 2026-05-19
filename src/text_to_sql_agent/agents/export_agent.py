"""Data export agent for query execution results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from text_to_sql_agent.services import export_query_result


def export_execution_result(
    execution_result: dict[str, Any],
    *,
    export_format: str = "csv",
    output_dir: str | Path | None = None,
) -> str:
    """Export previously executed result without re-running SQL."""
    return export_query_result(
        execution_result,
        export_format=export_format,
        output_dir=output_dir,
    )


def build_export_node(*, output_dir: str | Path | None = None, default_format: str = "csv"):
    """Return a LangGraph-compatible export node."""

    def node(state: dict) -> dict:
        result = state.get("execution_result")
        if not isinstance(result, dict):
            return {
                "export_path": None,
                "status": "failed",
                "error_message": "export: execution_result is missing",
                "log_messages": ["export: ERROR - execution_result is missing"],
            }

        export_format = str(state.get("export_format", default_format))
        try:
            export_path = export_execution_result(
                result,
                export_format=export_format,
                output_dir=output_dir,
            )
            return {
                "export_path": export_path,
                "log_messages": [
                    f"export: file written format={export_format} path={export_path}"
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "export_path": None,
                "status": "failed",
                "error_message": f"export: failed - {exc}",
                "log_messages": [f"export: ERROR - {exc}"],
            }

    return node
