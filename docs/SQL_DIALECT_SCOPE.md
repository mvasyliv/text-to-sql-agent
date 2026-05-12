# SQL Dialect Prompt Scope Matrix

This document defines a concise matrix of SQL dialect differences that affect prompt design and example selection.

Supported dialects:
- PostgreSQL
- MySQL
- Athena (Trino/Presto)
- SQLite

## Core Matrix

| Dialect | Identifier Quote | Date Bucket Pattern | String Aggregation | JSON Scalar Access | Null Handling | Case-Insensitive Filter |
| --- | --- | --- | --- | --- | --- | --- |
| PostgreSQL | `"identifier"` | `DATE_TRUNC('month', ts)` | `STRING_AGG(expr, ',')` | `payload ->> 'key'` | `COALESCE(a, b)` | `ILIKE` |
| MySQL | `` `identifier` `` | `DATE_FORMAT(ts, '%Y-%m-01')` | `GROUP_CONCAT(expr SEPARATOR ',')` | `JSON_UNQUOTE(JSON_EXTRACT(payload, '$.key'))` | `IFNULL(a, b)` | `LOWER(col) LIKE LOWER(pattern)` |
| Athena | `"identifier"` | `date_trunc('month', ts)` | `array_join(array_agg(expr), ',')` | `json_extract_scalar(payload, '$.key')` | `coalesce(a, b)` | `LOWER(col) LIKE LOWER(pattern)` |
| SQLite | `"identifier"` | `strftime('%Y-%m-01', ts)` | `GROUP_CONCAT(expr, ',')` | `json_extract(payload, '$.key')` | `IFNULL(a, b)` | `LOWER(col) LIKE LOWER(pattern)` |

## Prompt Scope Rules

### Cross-dialect baseline

- Generate read-only SQL (`SELECT`/`WITH` only).
- Always include a deterministic `LIMIT` unless a strict aggregate result naturally returns one row.
- Prefer explicit aliases for computed expressions.
- Avoid dialect-specific syntax unless the selected dialect requires it.

### PostgreSQL-specific rules

- Prefer `ILIKE` for case-insensitive text filters.
- Use `STRING_AGG` for grouped string outputs.
- Permit `DISTINCT ON` only with explicit deterministic ordering.

### MySQL-specific rules

- Do not emit `ILIKE`.
- Use `DATE_FORMAT` for canonical month buckets.
- Use `GROUP_CONCAT(... SEPARATOR ',')` for grouped string outputs.

### Athena-specific rules

- Use Trino/Presto-compatible function names and behavior.
- Use `CAST(expr AS type)`, not PostgreSQL `::type` casts.
- Use `array_join(array_agg(...), ',')` for grouped string outputs.

### SQLite-specific rules

- Use `strftime` for date bucketing.
- Use `GROUP_CONCAT(expr, ',')` for grouped string outputs.
- Assume JSON access through `json_extract` (JSON1 extension).

## Prompt Example Selection Guidance

When preparing few-shot examples:

- Keep one canonical aggregation example per dialect (monthly bucket + count).
- Keep one canonical grouped-string example per dialect.
- Keep JSON examples dialect-specific because extraction syntax differs significantly.
- Avoid examples that rely on proprietary features unless explicitly requested.

## Source of Truth in Code

The typed matrix for runtime prompt planning and tests is defined in:
- `src/text_to_sql_agent/prompts/dialect_scope.py`
