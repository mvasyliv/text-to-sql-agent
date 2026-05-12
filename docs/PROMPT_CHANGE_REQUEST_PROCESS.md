# Prompt Change Request Process

This document defines the required change request process for all prompt updates.

Typed process contract is implemented in:
- `src/text_to_sql_agent/prompts/change_request.py`

## Required Fields

Every change request must include:

- `request_id` in format `CRQ-YYYYMMDD-NNN`
- `change_type` (`standard` or `emergency_hotfix`)
- `status`
- `manifest_id`
- `current_version`
- `proposed_version` (must be greater than `current_version`)
- `requested_by`
- `owner`
- `summary`
- `rationale`
- `risk_assessment`
- `test_evidence`
- `rollback_plan`
- `approvers_required`
- `created_at`
- `updated_at`

For emergency hotfix requests, these additional fields are mandatory:

- `incident_id` (format `INC-<number>`)
- `expedited_approved_by` (at least two approvers)
- `postmortem_due_at` (within 72 hours of request creation)

## Review Flow

### Standard path

1. `draft`: Author prepares change request with required fields and evidence.
2. `submitted`: Request is posted for review.
3. `in_review`: Required approver roles review the request.
4. `approved` or `rejected`: Approval decision is finalized.
5. `implemented`: Approved change is deployed.
6. `closed`: Request and rollout outcomes are recorded.

Approval gate for `approved`, `implemented`, and `closed` states:
- all roles in `approvers_required` must provide approval.

### Emergency hotfix path

1. `submitted`: Incident-linked request is opened with `incident_id`.
2. `approved`: Fast-track approval with at least two `expedited_approved_by` identities.
3. `implemented`: Hotfix is deployed under incident timeline.
4. `postmortem_required`: Follow-up analysis is mandatory.
5. `closed`: Only after `postmortem_completed_at` is recorded.

Hotfix control rules:
- postmortem deadline must be set within 72 hours.
- request cannot be closed until postmortem completion is recorded.

## Required Approvers

Default required roles for standard requests:

- `prompt-owner`
- `data-platform`
- `security`

Teams may extend `approvers_required` for high-risk or tenant-sensitive prompts.

## Emergency Approval Guidance

Recommended expedited approver set:

- on-call engineering lead
- security on-call reviewer

If business-critical tenant impact is detected, add a product or incident commander approver before implementation.

## Evidence Expectations

Minimum evidence for standard changes:

- prompt diff summary
- regression or evaluation results
- SQL safety checks outcome
- rollback test or rollback dry-run plan

Minimum evidence for emergency hotfixes:

- incident link and blast radius
- quick validation output (smoke or targeted tests)
- postmortem owner and due date
