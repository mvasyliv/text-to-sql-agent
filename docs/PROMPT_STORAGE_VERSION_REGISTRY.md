# Prompt Storage And Version Registry Design

This document defines the selected approach for external prompt storage and version registry metadata.

Typed contract is implemented in:
- `src/text_to_sql_agent/prompts/storage_registry.py`

## Storage Approach

### External storage

Prompt template bodies are stored outside application code in object storage.

Supported backends in the contract:

- `s3`
- `azure_blob`
- `gcs`
- `postgres`
- `filesystem`

Storage configuration fields:

- `backend`
- `bucket_or_container`
- `namespace`
- `object_key_prefix`
- `region` (optional)

### Template URI constraints

Each prompt version references an immutable template location using `template_uri`.

Allowed URI schemes:

- `s3://`
- `gs://`
- `az://`
- `file://`

## Version Registry Rules

Each version record includes:

- `manifest_id`
- `version`
- `status` (`draft`, `review`, `approved`, `canary`, `active`, `retired`)
- `checksum_sha256`
- `template_uri`
- `ownership`
- timestamps (`created_at`, `updated_at`)
- actors (`created_by`, `updated_by`)

Registry-level pointers:

- `latest_version`: must equal the highest existing version
- `active_version`: if set, must reference a record with status `active`
- `canary_version`: if set, must reference a record with status `canary`

All records in one registry must share the same `manifest_id`.

## Ownership Rules

Ownership is explicitly tracked for each version:

- `owner_type`: `team`, `user`, or `service-account`
- `owner_id`
- `contact_channel`

This metadata supports accountability for approvals, incidents, and rollbacks.

## Integrity Rules

- `checksum_sha256` must be a 64-char lowercase hex SHA-256 value.
- `updated_at` cannot be earlier than `created_at`.
- Version numbers are monotonic and positive integers.

## Operational Guidance

- Treat prompt templates as immutable artifacts per version.
- Promote status through lifecycle (`draft` -> `review` -> `approved` -> `canary` -> `active`).
- Keep registry pointers synchronized with status transitions.
- Use change request governance before changing active or canary pointers.
