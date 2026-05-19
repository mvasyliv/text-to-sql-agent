"""Tests for query result export service (T-2026-05-18-048)."""

import json
from pathlib import Path

import pytest

from text_to_sql_agent.services import export_query_result


def _execution_result() -> dict:
    return {
        "columns": ["id", "name"],
        "rows": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ],
    }


def test_export_query_result_csv(tmp_path: Path):
    path = export_query_result(
        _execution_result(),
        export_format="csv",
        output_dir=tmp_path,
        file_stem="users",
    )

    content = Path(path).read_text(encoding="utf-8")
    assert path.endswith(".csv")
    assert "id,name" in content
    assert "Alice" in content


def test_export_query_result_json(tmp_path: Path):
    path = export_query_result(
        _execution_result(),
        export_format="json",
        output_dir=tmp_path,
        file_stem="users",
    )

    assert path.endswith(".json")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert payload["row_count"] == 2
    assert payload["rows"][1]["name"] == "Bob"


def test_export_query_result_unsupported_format(tmp_path: Path):
    with pytest.raises(ValueError):
        export_query_result(
            _execution_result(),
            export_format="xml",
            output_dir=tmp_path,
        )


def test_export_query_result_requires_rows(tmp_path: Path):
    with pytest.raises(ValueError):
        export_query_result(
            {"columns": ["id"]},
            export_format="csv",
            output_dir=tmp_path,
        )
