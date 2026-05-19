"""Utilities for exporting query execution results to files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


_SUPPORTED_EXPORT_FORMATS = {"csv", "json", "xlsx"}


def _normalize_export_format(export_format: str) -> str:
    normalized = export_format.strip().lower()
    if normalized not in _SUPPORTED_EXPORT_FORMATS:
        supported = ", ".join(sorted(_SUPPORTED_EXPORT_FORMATS))
        raise ValueError(
            f"Unsupported export format '{export_format}'. Supported formats: {supported}"
        )
    return normalized


def _resolve_output_path(
    *,
    export_format: str,
    output_dir: str | Path | None = None,
    file_stem: str = "query_result",
) -> Path:
    directory = Path(output_dir) if output_dir is not None else Path("/tmp")
    directory.mkdir(parents=True, exist_ok=True)
    suffix = ".json" if export_format == "json" else f".{export_format}"
    return directory / f"{file_stem}_{uuid4().hex[:8]}{suffix}"


def export_query_result(
    execution_result: dict[str, Any],
    *,
    export_format: str = "csv",
    output_dir: str | Path | None = None,
    file_stem: str = "query_result",
) -> str:
    """Export tabular query execution result into a file path.

    Expected execution_result shape:
    - rows: list[dict[str, Any]]
    - columns: list[str]
    """
    fmt = _normalize_export_format(export_format)

    rows = execution_result.get("rows")
    if not isinstance(rows, list):
        raise ValueError("execution_result must contain list field 'rows'")

    columns = execution_result.get("columns")
    if not isinstance(columns, list):
        # derive columns from first row when available
        columns = list(rows[0].keys()) if rows and isinstance(rows[0], dict) else []

    output_path = _resolve_output_path(
        export_format=fmt,
        output_dir=output_dir,
        file_stem=file_stem,
    )

    if fmt == "csv":
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[str(col) for col in columns])
            writer.writeheader()
            for row in rows:
                if isinstance(row, dict):
                    writer.writerow(row)
                else:
                    writer.writerow({"value": row})
        return str(output_path)

    if fmt == "json":
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "columns": columns,
                    "row_count": len(rows),
                    "rows": rows,
                },
                handle,
                ensure_ascii=True,
                indent=2,
            )
        return str(output_path)

    # xlsx (optional dependency)
    try:
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover
        raise ValueError(
            "XLSX export requires optional dependency 'openpyxl'"
        ) from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "query_result"
    if columns:
        sheet.append([str(col) for col in columns])
    for row in rows:
        if isinstance(row, dict):
            sheet.append([row.get(col) for col in columns])
        else:
            sheet.append([row])
    workbook.save(output_path)
    return str(output_path)
