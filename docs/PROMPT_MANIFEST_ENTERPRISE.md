# Enterprise Prompt Manifest Contract

This document defines the enterprise manifest contract for multi-tenant isolation, compliance, auditability, approval workflow, and controlled rollout.

The contract is implemented in code at:
- `src/text_to_sql_agent/prompts/prompt_manifest.py`

It extends the MVP baseline in:
- `docs/PROMPT_MANIFEST_MVP.md`

## Enterprise-Only Fields

| Field | Type | Required | Rules | Purpose |
| --- | --- | --- | --- | --- |
| `environment` | enum | yes | `dev`, `staging`, `prod` | Deployment environment scope |
| `tenant_policy.mode` | enum | yes | `single_tenant`, `tenant_allowlist` | Isolation mode |
| `tenant_policy.tenant_id` | string | yes | Stable tenant id format | Primary tenant |
| `tenant_policy.allowed_tenant_ids` | string[] | conditional | Required for allowlist mode; unique; includes `tenant_id` | Explicit tenant sharing scope |
| `audit.created_by` | string | yes | Non-empty | Author traceability |
| `audit.updated_by` | string | yes | Non-empty | Last editor traceability |
| `audit.created_at` | datetime | yes | UTC timestamp | Creation audit |
| `audit.updated_at` | datetime | yes | Must be `>= created_at` | Update audit |
| `audit.change_ticket` | string | yes | Pattern like `DATA-123` | Change control linkage |
| `audit.checksum_sha256` | string | yes | 64 lowercase hex chars | Template integrity check |
| `approval.status` | enum | yes | `pending`, `approved`, `rejected` | Approval state |
| `approval.required_reviewers` | string[] | yes | Non-empty and unique | Required approver roles |
| `approval.approved_by` | string | conditional | Required only when `status=approved` | Approver identity |
| `approval.approved_at` | datetime | conditional | Required only when `status=approved` | Approval timestamp |
| `approval.policy_level` | enum | yes | `low_risk`, `standard`, `strict` | Rollout governance strictness |
| `compliance_tags` | string[] | yes | Non-empty, normalized lowercase, unique | Compliance classification |

## Enterprise Validation Rules

- Active enterprise manifests require `approval.status=approved`.
- Tenant isolation must be explicit:
  - `single_tenant`: no `allowed_tenant_ids` allowed.
  - `tenant_allowlist`: `allowed_tenant_ids` is required and must contain `tenant_id`.
- Audit metadata must be internally consistent (`updated_at >= created_at`).
- Approval metadata must be internally consistent:
  - `approved` requires `approved_by` and `approved_at`.
  - non-`approved` statuses must not contain approval actor/time.

## Rollout Policy Levels

### `low_risk`

- Suitable for low-impact environments and non-sensitive tenants.
- Uses standard MVP rollout constraints (`off`, `canary`, `full`) based on status.

### `standard`

- Baseline enterprise governance.
- In `prod`, active manifests cannot use `rollout.strategy=off`.

### `strict`

- High-sensitivity production governance.
- In `prod` and `active` state:
  - rollout must be `canary`
  - canary percentage must be `<= 25`
- Full rollout is blocked until strict canary promotion is completed.
