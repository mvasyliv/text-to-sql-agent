"""SQL syntax validator agent for MVP query pipeline.

The validator is intentionally deterministic and conservative:
- rejects empty SQL
- requires a single statement
- requires SELECT/WITH entrypoint
- rejects disallowed write/DDL operations
- checks balanced parentheses and quotes
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_DISALLOWED_OPERATIONS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "MERGE",
    "GRANT",
    "REVOKE",
    "CREATE",
)


@dataclass(frozen=True, slots=True)
class SQLSyntaxValidationResult:
    """Result of SQL syntax validation."""

    valid: bool
    errors: list[str]


def _single_statement(sql: str) -> bool:
    statements = [part.strip() for part in sql.split(";") if part.strip()]
    return len(statements) == 1


def _has_balanced_parentheses(sql: str) -> bool:
    depth = 0
    for ch in sql:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _has_balanced_single_quotes(sql: str) -> bool:
    # Simple SQL-style escaping: doubled single-quote does not toggle state.
    in_quote = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'":
            if i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_quote = not in_quote
        i += 1
    return not in_quote


def _starts_with_allowed_statement(sql: str) -> bool:
    first = sql.lstrip().split(maxsplit=1)[0].upper() if sql.strip() else ""
    return first in {"SELECT", "WITH"}


def _find_disallowed_operation(sql: str) -> str | None:
    upper_sql = sql.upper()
    for keyword in _DISALLOWED_OPERATIONS:
        if re.search(rf"\b{re.escape(keyword)}\b", upper_sql):
            return keyword
    return None


def validate_sql_syntax(sql: str) -> SQLSyntaxValidationResult:
    """Validate SQL text for MVP read-only syntax constraints."""
    if not isinstance(sql, str):
        raise TypeError("SQL must be a string")

    normalized = sql.strip()
    errors: list[str] = []

    if not normalized:
        errors.append("SQL is empty")

    if normalized and not _single_statement(normalized):
        errors.append("Only a single SQL statement is allowed")

    if normalized and not _starts_with_allowed_statement(normalized):
        errors.append("SQL must start with SELECT or WITH")

    blocked = _find_disallowed_operation(normalized) if normalized else None
    if blocked is not None:
        errors.append(f"Disallowed operation detected: {blocked}")

    if normalized and not _has_balanced_parentheses(normalized):
        errors.append("Unbalanced parentheses detected")

    if normalized and not _has_balanced_single_quotes(normalized):
        errors.append("Unbalanced single quotes detected")

    return SQLSyntaxValidationResult(valid=(len(errors) == 0), errors=errors)


def build_syntax_validator_node():
    """Return a LangGraph-compatible syntax validator node."""

    def node(state: dict) -> dict:
        sql = state.get("edited_sql") or state.get("generated_sql") or ""
        try:
            result = validate_sql_syntax(sql)
            return {
                "syntax_valid": result.valid,
                "syntax_errors": result.errors,
                "status": "validating" if result.valid else "failed",
                "log_messages": [
                    f"syntax_validator: valid={result.valid}, errors={len(result.errors)}"
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "syntax_valid": False,
                "syntax_errors": [str(exc)],
                "status": "failed",
                "error_message": f"syntax_validator: failed - {exc}",
                "log_messages": [f"syntax_validator: ERROR - {exc}"],
            }

    return node
