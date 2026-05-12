# MVP Prompt Manifest Contract

This document defines the minimal prompt manifest contract required for safe read-only SQL generation and basic rollout control in MVP.

The contract is implemented in code at:
- `src/text_to_sql_agent/prompts/prompt_manifest.py`

Enterprise extension of this baseline is documented in:
- `docs/PROMPT_MANIFEST_ENTERPRISE.md`

The dialect scope baseline consumed by this contract is defined at:
- `docs/SQL_DIALECT_SCOPE.md`
- `src/text_to_sql_agent/prompts/dialect_scope.py`

## Contract Fields (MVP)

| Field | Type | Required | Rules | Purpose |
| --- | --- | --- | --- | --- |
| `manifest_id` | string | yes | Pattern `^[a-zA-Z0-9._:-]+$` | Stable prompt identity |
| `version` | integer | yes | `>= 1` | Monotonic prompt version |
| `dialect` | enum | yes | One of `postgresql`, `mysql`, `athena`, `sqlite` | Selects dialect-specific prompt scope |
| `status` | enum | yes | `draft` or `active` | Lifecycle state |
| `owner` | string | yes | Non-empty | Ownership and accountability |
| `prompt_template` | string | yes | Must include `{user_request}` and `{schema_context}` | Renderable prompt body |
| `read_only_required` | boolean | yes | Must be `true` in MVP | Safety baseline |
| `max_limit` | integer | yes | `1..10000` | Query limit cap |
| `required_guardrails` | string[] | yes | Must include `select_or_with_only` | Runtime guardrail baseline |
| `disallowed_operations` | string[] | yes | Normalized uppercase, unique | Explicit deny list |
| `rollout.strategy` | enum | yes | `off`, `canary`, `full` | Basic rollout control |
| `rollout.percentage` | integer | yes | `off -> 0`, `full -> 100`, `canary -> 1..99` | Traffic split |
| `created_at` | datetime | yes | UTC timestamp | Auditability |
| `notes` | string | no | Optional | Operational notes |

## MVP Safety Rules

- Manifest must enforce read-only generation (`read_only_required=true`).
- Prompt template must include both placeholders:
  - `{user_request}`
  - `{schema_context}`
- Guardrails must include at least:
  - `single_statement`
  - `select_or_with_only`
  - `enforce_limit`
  - `deny_dml_ddl`
- Deny list defaults include DML and DDL operations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, and related operations).

## MVP Rollout Rules

- `draft` manifests may use `rollout.strategy=off`.
- `active` manifests must use `rollout.strategy=canary` or `rollout.strategy=full`.
- Canary rollout requires `rollout.percentage` in `1..99`.

## Example (Draft)

```json
{
  "manifest_id": "mvp.sales.monthly",
  "version": 1,
  "dialect": "postgresql",
  "status": "draft",
  "owner": "analytics-team",
  "prompt_template": "Question: {user_request}\nSchema: {schema_context}\nReturn one read-only SQL query.",
  "read_only_required": true,
  "max_limit": 1000,
  "required_guardrails": [
    "single_statement",
    "select_or_with_only",
    "enforce_limit",
    "deny_dml_ddl"
  ],
  "disallowed_operations": [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER"
  ],
  "rollout": {
    "strategy": "off",
    "percentage": 0
  }
}
```
