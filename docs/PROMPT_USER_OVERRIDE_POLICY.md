# Prompt User Override Policy

This document defines which prompt sections users may customize and which safety-critical sections are immutable.

Typed policy contract is implemented in:
- `src/text_to_sql_agent/prompts/override_policy.py`

## Customizable Sections

Users may override only the following sections:

- `style_instructions`
- `business_glossary`
- `few_shot_examples`
- `response_format_hint`
- `domain_filters`

These sections are intended for tenant or team-specific guidance that does not weaken SQL safety controls.

## Immutable Sections

The following sections are immutable and cannot be overridden by users:

- `safety_guardrails`
- `required_placeholders`
- `disallowed_operations`
- `read_only_enforcement`
- `tenant_isolation`
- `approval_workflow`

These sections enforce non-negotiable safety and governance requirements.

## Validation Boundaries

Every override request must pass all checks below:

1. Section boundary check:
   - reject if section is immutable
   - reject if section is not listed as customizable
2. Payload size check:
   - reject if override payload exceeds `max_override_payload_chars`
3. Rationale check:
   - reject if rationale is empty when rationale is required

## Default Policy Values

- `policy_id`: `override-policy-v1`
- `max_override_payload_chars`: `4000`
- `require_non_empty_rationale`: `true`

## Governance Integration

- Any accepted user override should still follow prompt manifest and change request governance before activation.
- Immutable section changes must go through governed prompt updates rather than user overrides.
