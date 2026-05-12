# Prompt Metrics And Evaluation Gates

This document defines quality and safety gates used to evaluate prompt versions before promotion.

Typed contract is implemented in:
- `src/text_to_sql_agent/prompts/evaluation_gates.py`

## Required Metrics

Each evaluation scorecard must provide these metrics as values in `[0.0, 1.0]`:

- `validity_rate`
- `execution_success_rate`
- `policy_violation_rate`
- `leakage_rate`

## Default Gate Thresholds

| Metric | Direction | Threshold | Hard Fail |
| --- | --- | --- | --- |
| `validity_rate` | higher is better | `>= 0.98` | yes |
| `execution_success_rate` | higher is better | `>= 0.95` | yes |
| `policy_violation_rate` | lower is better | `<= 0.01` | yes |
| `leakage_rate` | lower is better | `<= 0.005` | yes |

Default profile metadata:

- `profile_id`: `default-v1`
- `minimum_samples`: `50`

## Gate Decision Rules

- If any required metric is missing, gate fails.
- If any hard-fail threshold is violated, gate fails.
- If sample size is below `minimum_samples`, add a warning.
- Warnings alone do not block promotion; blocking violations do.

## Scorecard Contract

Each scorecard includes:

- `manifest_id`
- `version`
- `sample_size`
- metric scores (`metric_name`, `value`)

Metric names in one scorecard must be unique.

## Operational Guidance

- Run evaluation gates before changing canary/active pointers.
- Keep metric definitions stable across prompt versions to support trend analysis.
- Tighten thresholds only through governed change requests.
