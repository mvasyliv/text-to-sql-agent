"""Shared MCP security policy for read-only query execution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

_READ_ONLY_ENTRYPOINTS = ("select", "with")
_DEFAULT_DENIED_OPERATIONS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "merge",
    "grant",
    "revoke",
    "create",
    "replace",
)

_SCHEMA_TOKEN_PATTERN = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w$]*)\.([a-zA-Z_][\w$]*)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class MCPSecurityValidationResult:
    """Result of shared MCP SQL policy validation."""

    approved: bool
    violations: list[str]
    referenced_schemas: list[str]


def _extract_referenced_schemas(sql_query: str) -> list[str]:
    matches = _SCHEMA_TOKEN_PATTERN.findall(sql_query)
    seen: set[str] = set()
    schemas: list[str] = []
    for schema_name, _table_name in matches:
        normalized = schema_name.lower()
        if normalized not in seen:
            seen.add(normalized)
            schemas.append(normalized)
    return schemas


def validate_mcp_sql_policy(
    sql_query: str,
    *,
    allowed_schemas: Iterable[str] | None = None,
    denied_operations: Iterable[str] | None = None,
) -> MCPSecurityValidationResult:
    """Validate SQL against shared MCP execution policy constraints."""
    if not isinstance(sql_query, str):
        raise TypeError("SQL query must be a string")

    normalized_sql = sql_query.strip()
    violations: list[str] = []

    if not normalized_sql:
        return MCPSecurityValidationResult(
            approved=False,
            violations=["empty_sql"],
            referenced_schemas=[],
        )

    first_token = normalized_sql.lstrip("(").split(maxsplit=1)[0].lower()
    if first_token not in _READ_ONLY_ENTRYPOINTS:
        violations.append("non_read_only_entrypoint")

    operations = tuple(op.lower() for op in (denied_operations or _DEFAULT_DENIED_OPERATIONS))
    for operation in operations:
        if re.search(rf"\b{re.escape(operation)}\b", normalized_sql, flags=re.IGNORECASE):
            violations.append(f"denied_operation:{operation}")

    referenced_schemas = _extract_referenced_schemas(normalized_sql)
    if allowed_schemas is not None:
        allowed = {schema.strip().lower() for schema in allowed_schemas if schema and schema.strip()}
        for schema_name in referenced_schemas:
            if schema_name not in allowed:
                violations.append(f"schema_not_allowed:{schema_name}")

    return MCPSecurityValidationResult(
        approved=(len(violations) == 0),
        violations=violations,
        referenced_schemas=referenced_schemas,
    )


def enforce_mcp_sql_policy(sql_query: str, connection_config: dict) -> None:
    """Raise ValueError when SQL violates shared MCP execution policy."""
    allowed_schemas = (
        connection_config.get("mcp_allowed_schemas")
        or connection_config.get("allowed_schemas")
        or None
    )

    result = validate_mcp_sql_policy(
        sql_query,
        allowed_schemas=allowed_schemas,
    )
    if result.approved:
        return

    if "non_read_only_entrypoint" in result.violations:
        raise ValueError(
            "Only read-only SELECT or WITH statements are allowed by MCP security policy"
        )

    raise ValueError(
        "MCP security policy violations: " + ", ".join(result.violations)
    )
