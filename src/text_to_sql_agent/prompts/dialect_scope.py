"""SQL dialect scope matrix for prompt planning and validation.

This module provides a concise, typed matrix of SQL dialect differences that
drive prompt instructions and example selection.
"""

from dataclasses import dataclass
from typing import Literal


DialectName = Literal["postgresql", "mysql", "athena", "sqlite"]


@dataclass(frozen=True)
class DialectPromptScope:
    """Prompt-relevant SQL dialect constraints and canonical examples."""

    name: DialectName
    identifier_quote: str
    limit_syntax: str
    date_bucket_expression: str
    string_aggregation_expression: str
    null_function: str
    json_scalar_expression: str
    notes: tuple[str, ...]
    prompt_requirements: tuple[str, ...]
    examples: tuple[str, ...]


DIALECT_SCOPE_MATRIX: dict[DialectName, DialectPromptScope] = {
    "postgresql": DialectPromptScope(
        name="postgresql",
        identifier_quote='"identifier"',
        limit_syntax="LIMIT {n}",
        date_bucket_expression="DATE_TRUNC('month', ts)",
        string_aggregation_expression="STRING_AGG(expr, ',')",
        null_function="COALESCE(a, b)",
        json_scalar_expression="payload ->> 'key'",
        notes=(
            "Supports DISTINCT ON and FILTER in aggregates.",
            "ILIKE is available for case-insensitive text search.",
        ),
        prompt_requirements=(
            "Prefer ILIKE for case-insensitive predicates.",
            "Use STRING_AGG for grouped string output.",
            "Allow DISTINCT ON only when deterministic ordering is present.",
        ),
        examples=(
            "SELECT DATE_TRUNC('month', created_at) AS month_bucket, COUNT(*) AS order_count FROM orders GROUP BY 1 ORDER BY 1 LIMIT 12;",
            "SELECT customer_id, STRING_AGG(status, ',') AS statuses FROM order_events GROUP BY customer_id LIMIT 100;",
        ),
    ),
    "mysql": DialectPromptScope(
        name="mysql",
        identifier_quote="`identifier`",
        limit_syntax="LIMIT {n}",
        date_bucket_expression="DATE_FORMAT(ts, '%Y-%m-01')",
        string_aggregation_expression="GROUP_CONCAT(expr SEPARATOR ',')",
        null_function="IFNULL(a, b)",
        json_scalar_expression="JSON_UNQUOTE(JSON_EXTRACT(payload, '$.key'))",
        notes=(
            "No ILIKE support; use LOWER(col) LIKE LOWER(pattern).",
            "Window function support is version-dependent.",
        ),
        prompt_requirements=(
            "Never emit ILIKE.",
            "Use GROUP_CONCAT for grouped string output.",
            "Use DATE_FORMAT for monthly bucket examples.",
        ),
        examples=(
            "SELECT DATE_FORMAT(created_at, '%Y-%m-01') AS month_bucket, COUNT(*) AS order_count FROM orders GROUP BY month_bucket ORDER BY month_bucket LIMIT 12;",
            "SELECT customer_id, GROUP_CONCAT(status SEPARATOR ',') AS statuses FROM order_events GROUP BY customer_id LIMIT 100;",
        ),
    ),
    "athena": DialectPromptScope(
        name="athena",
        identifier_quote='"identifier"',
        limit_syntax="LIMIT {n}",
        date_bucket_expression="date_trunc('month', ts)",
        string_aggregation_expression="array_join(array_agg(expr), ',')",
        null_function="coalesce(a, b)",
        json_scalar_expression="json_extract_scalar(payload, '$.key')",
        notes=(
            "Athena follows Trino/Presto SQL behavior.",
            "Avoid PostgreSQL-only operators such as ::type casts.",
        ),
        prompt_requirements=(
            "Use date_trunc and explicit CAST instead of :: shortcuts.",
            "Use array_join(array_agg(...)) for grouped string output.",
            "Use json_extract_scalar for scalar JSON fields.",
        ),
        examples=(
            "SELECT date_trunc('month', created_at) AS month_bucket, COUNT(*) AS order_count FROM orders GROUP BY 1 ORDER BY 1 LIMIT 12;",
            "SELECT customer_id, array_join(array_agg(status), ',') AS statuses FROM order_events GROUP BY customer_id LIMIT 100;",
        ),
    ),
    "sqlite": DialectPromptScope(
        name="sqlite",
        identifier_quote='"identifier"',
        limit_syntax="LIMIT {n}",
        date_bucket_expression="strftime('%Y-%m-01', ts)",
        string_aggregation_expression="GROUP_CONCAT(expr, ',')",
        null_function="IFNULL(a, b)",
        json_scalar_expression="json_extract(payload, '$.key')",
        notes=(
            "Date and time handling relies on strftime helpers.",
            "JSON operators depend on JSON1 extension availability.",
        ),
        prompt_requirements=(
            "Use strftime for date bucket examples.",
            "Use GROUP_CONCAT for grouped string output.",
            "Prefer IFNULL for simple null fallback patterns.",
        ),
        examples=(
            "SELECT strftime('%Y-%m-01', created_at) AS month_bucket, COUNT(*) AS order_count FROM orders GROUP BY month_bucket ORDER BY month_bucket LIMIT 12;",
            "SELECT customer_id, GROUP_CONCAT(status, ',') AS statuses FROM order_events GROUP BY customer_id LIMIT 100;",
        ),
    ),
}


def get_dialect_prompt_scope(dialect: str) -> DialectPromptScope:
    """Return prompt scope details for a supported SQL dialect.

    Args:
        dialect: SQL dialect name (case-insensitive).

    Raises:
        ValueError: If the dialect is unsupported.
    """
    normalized = dialect.strip().lower()
    scope = DIALECT_SCOPE_MATRIX.get(normalized)
    if scope is None:
        supported = ", ".join(sorted(DIALECT_SCOPE_MATRIX))
        raise ValueError(f"Unsupported dialect '{dialect}'. Supported: {supported}")
    return scope


def list_supported_dialects() -> tuple[DialectName, ...]:
    """List supported SQL dialects in stable alphabetical order."""
    return tuple(sorted(DIALECT_SCOPE_MATRIX))
