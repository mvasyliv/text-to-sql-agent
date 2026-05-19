"""Tests for export agent (T-2026-05-18-048)."""

from pathlib import Path

from text_to_sql_agent.agents import build_export_node, export_execution_result


def _execution_result() -> dict:
    return {
        "database_id": "db1",
        "dialect": "sqlite",
        "sql": "SELECT id, name FROM users",
        "columns": ["id", "name"],
        "rows": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ],
        "row_count": 2,
    }


def test_export_execution_result_csv(tmp_path: Path):
    export_path = export_execution_result(
        _execution_result(),
        export_format="csv",
        output_dir=tmp_path,
    )

    assert export_path.endswith(".csv")
    assert Path(export_path).exists()


def test_build_export_node_success(tmp_path: Path):
    node = build_export_node(output_dir=tmp_path, default_format="json")
    result = node({"execution_result": _execution_result()})

    assert result["export_path"] is not None
    assert result["export_path"].endswith(".json")
    assert "file written" in result["log_messages"][0]


def test_build_export_node_failure_when_missing_execution_result(tmp_path: Path):
    node = build_export_node(output_dir=tmp_path)
    result = node({})

    assert result["export_path"] is None
    assert result["status"] == "failed"
    assert "execution_result is missing" in result["error_message"]


def test_build_export_node_uses_explicit_format_from_state(tmp_path: Path):
    node = build_export_node(output_dir=tmp_path, default_format="csv")
    result = node({"execution_result": _execution_result(), "export_format": "json"})

    assert result["export_path"].endswith(".json")
