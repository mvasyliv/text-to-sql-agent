# Project Decisions

This file records durable project-level decisions that affect how work is documented or executed.

Rules:
- Record only decisions that should remain visible over time.
- Reference related task IDs where applicable.
- Write every entry in English.

## D-2026-05-11-001

- Date: 2026-05-11
- Related task: T-2026-05-11-001
- Decision: All project tasks must be recorded in `docs/TASKS.md`, with supporting execution history kept in `docs/WORKLOG.md` and durable decisions recorded in this file.
- Decision: All documentation, comments, and project-facing technical explanations must be written in English, regardless of the user's language.
- Rationale: This keeps project history centralized, reviewable, and consistent across contributors and future sessions.

## D-2026-05-11-002

- Date: 2026-05-11
- Related task: T-2026-05-11-002
- Decision: The repository must maintain `docs/CHANGELOG.md` to record notable project changes in a reader-friendly format.
- Decision: `docs/WORKLOG.md` remains the execution log, while `docs/CHANGELOG.md` summarizes externally relevant project changes.
- Rationale: This separates internal implementation history from a concise project change history and makes review easier over time.

## D-2026-05-11-003

- Date: 2026-05-11
- Related task: T-2026-05-11-003
- Decision: The canonical changelog location for this repository is `docs/CHANGELOG.md`, not the repository root.
- Rationale: This keeps all project documentation and history artifacts grouped under `docs/`.

## D-2026-05-11-004

- Date: 2026-05-11
- Related task: T-2026-05-11-004
- Decision: `docs/ARCHITECTURE.md` is the living reference for the intended system architecture and should be updated when the structure or request flow changes materially.
- Decision: Until implementation details exist, the architecture document may describe the target design explicitly instead of pretending the code already exists.
- Rationale: This keeps design intent visible early and reduces drift between planned structure and future implementation.

## D-2026-05-11-005

- Date: 2026-05-11
- Related task: T-2026-05-11-005
- Decision: `venvtext2sql/` is the canonical virtual environment for this project.
- Decision: `uv` is the canonical package manager; all dependency operations must use `uv` and never `pip`.
- Decision: `uv.lock` is the source of truth for pinned dependency versions and must be committed alongside `pyproject.toml`.
- Decision: VS Code is configured automatically to use `venvtext2sql` as the default Python interpreter via `.vscode/settings.json`.
- Rationale: This ensures reproducible builds, a single source of truth for dependency versions, and automatic environment activation for a frictionless developer experience.

## D-2026-05-11-006

- Date: 2026-05-11
- Related task: T-2026-05-11-010 (scope planning for prompt manifest and governance)
- Decision: Workspace-specific IDE settings (e.g., Markdown Preview styling, optional extensions) that do not affect code behavior must be stored locally in the user's VS Code profile, not in `.vscode/settings.json`.
- Decision: `${VSCODE_USER_PROMPTS_FOLDER}/../User/settings.json` (typically `~/.config/Code/User/settings.json` on Linux) is the prescribed location for personal workspace customizations.
- Decision: `.vscode/` directory is in `.gitignore` to prevent IDE configuration drift across team members.
- Rationale: This separates project-essential configuration (Python interpreter, linting) from personal IDE preferences (preview styling, extensions), avoiding unnecessary git changes and respecting individual developer workflow choices.

### Local Markdown Preview Setup (Optional)

To enable GitHub-like table rendering in VS Code Markdown Preview for this workspace:

1. Open VS Code **User Settings** (Ctrl+Shift+P → "Preferences: Open User Settings (JSON)").
2. Add the following snippet to `~/.config/Code/User/settings.json`:
   ```json
   "markdown.preview.fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
   "markdown.preview.lineHeight": 1.6,
   "markdown.preview.typographer": false,
   "markdown.preview.scrollPreviewWithEditor": true,
   "markdown.preview.scrollEditorWithPreview": true,
   "markdown.preview.doubleClickToSwitchToEditor": true
   ```
3. (Optional) Install the recommended extension: **GitHub Markdown Preview** (bierner.github-markdown-preview).
4. Open any `.md` file and press **Ctrl+Shift+V** (Markdown Preview) or **Ctrl+K, V** (Preview to the side).

This setup remains local to your VS Code profile and does not appear in `git status`.

## D-2026-05-11-007

- Date: 2026-05-11
- Related task: T-2026-05-11-010 (scope planning for prompt manifest and governance)
- Decision: Recommended VS Code extensions for this project are listed in `.vscode/extensions.json` to guide contributors toward a consistent developer experience.
- Decision: All extensions listed are for productivity, code quality, or collaboration only. No extension is required to run or test code; all are optional tools to enhance local workflow.
- Rationale: VS Code's extension recommendation system allows contributors to adopt a standard toolchain with one click ("Install All Recommended") without enforcing mandatory installation. This balances team consistency with individual choice.

## D-2026-05-12-008

- Date: 2026-05-12
- Related task: T-2026-05-11-010
- Decision: Prompt planning for SQL generation must use a dialect-specific scope matrix covering PostgreSQL, MySQL, Athena, and SQLite.
- Decision: The typed source of truth is `src/text_to_sql_agent/prompts/dialect_scope.py`, while `docs/SQL_DIALECT_SCOPE.md` is the human-readable reference.
- Decision: Dialect examples in the matrix must remain read-only (`SELECT`/`WITH`) and are validated by automated tests.
- Rationale: SQL syntax differences across dialects are a frequent source of invalid model output. A single scoped matrix reduces drift and keeps prompt constraints testable.

## D-2026-05-12-009

- Date: 2026-05-12
- Related task: T-2026-05-11-011
- Decision: The repository adopts an MVP prompt manifest contract with mandatory fields for identity, version, dialect, ownership, template placeholders, read-only enforcement, guardrails, deny-list operations, and rollout settings.
- Decision: The typed source of truth is `src/text_to_sql_agent/prompts/prompt_manifest.py`, while `docs/PROMPT_MANIFEST_MVP.md` is the human-readable contract reference.
- Decision: MVP rollout control supports `off`, `canary`, and `full` strategies with strict percentage constraints; `active` manifests cannot use `off`.
- Rationale: This defines a minimal but enforceable prompt lifecycle contract that keeps SQL generation safe (read-only) while allowing controlled rollout progression.

## D-2026-05-12-010

- Date: 2026-05-12
- Related task: T-2026-05-11-012
- Decision: The repository adopts an enterprise prompt manifest extension that requires explicit tenant isolation policy, audit metadata, approval metadata, and compliance tags.
- Decision: Enterprise rollout governance uses policy levels (`low_risk`, `standard`, `strict`) where strict production activation requires canary rollout with percentage `<= 25`.
- Decision: Active enterprise manifests require `approval.status=approved` with approver identity and approval timestamp.
- Rationale: Enterprise environments need stronger governance for multi-tenant safety, auditability, and controlled rollout than MVP-only constraints provide.

## D-2026-05-12-011

- Date: 2026-05-12
- Related task: T-2026-05-11-013
- Decision: All prompt updates must use a formal change request contract with required fields for scope summary, rationale, risk assessment, test evidence, and rollback plan.
- Decision: Standard requests require approvals from `prompt-owner`, `data-platform`, and `security` roles before approved/implemented/closed states.
- Decision: Emergency hotfix requests require incident linkage, at least two expedited approvers, and a postmortem deadline within 72 hours; closure requires postmortem completion timestamp.
- Rationale: Prompt updates are operationally sensitive and need a consistent review process with auditable controls and explicit emergency handling.

## D-2026-05-12-012

- Date: 2026-05-12
- Related task: T-2026-05-11-014
- Decision: User prompt overrides are allowed only for non-safety sections (`style_instructions`, `business_glossary`, `few_shot_examples`, `response_format_hint`, `domain_filters`).
- Decision: Safety and governance sections are immutable for user overrides (`safety_guardrails`, `required_placeholders`, `disallowed_operations`, `read_only_enforcement`, `tenant_isolation`, `approval_workflow`).
- Decision: Override validation must enforce section boundaries, payload size limits, and rationale requirements.
- Rationale: This preserves safety-critical prompt controls while still allowing scoped user customization for domain and formatting needs.

## D-2026-05-12-013

- Date: 2026-05-12
- Related task: T-2026-05-11-015
- Decision: Prompt template bodies are stored externally and referenced by immutable `template_uri` values in a typed version registry.
- Decision: Registry pointer fields must remain consistent: `latest_version` equals max version, `active_version` points to status `active`, and `canary_version` points to status `canary`.
- Decision: Every version record must include `checksum_sha256` and explicit ownership metadata (`owner_type`, `owner_id`, `contact_channel`).
- Rationale: Externalized prompt storage with strict registry metadata improves integrity, traceability, and controlled rollout operations.

## D-2026-05-12-014

- Date: 2026-05-12
- Related task: T-2026-05-11-016
- Decision: Prompt promotion decisions must use a typed evaluation gate profile over required metrics: `validity_rate`, `execution_success_rate`, `policy_violation_rate`, and `leakage_rate`.
- Decision: Default profile `default-v1` enforces hard-fail thresholds: validity `>= 0.98`, execution success `>= 0.95`, policy violations `<= 0.01`, leakage `<= 0.005`.
- Decision: Missing required metrics and hard-fail threshold breaches block promotion; low sample size creates warnings and is tracked separately.
- Rationale: Explicit quantitative gates reduce subjective promotion decisions and keep safety regressions detectable before rollout.

## D-2026-05-12-015

- Date: 2026-05-12
- Related task: T-2026-05-12-017
- Decision: Test directory structure must mirror source package structure under `tests/text_to_sql_agent/<package>/...` for modules in `src/text_to_sql_agent/<package>/...`.
- Decision: The repository keeps an explicit mirrored directory skeleton for `agents`, `config`, `graphs`, `models`, `prompts`, `repositories`, `services`, and `utils`.
- Decision: Test placement rule is enforced in project and tester instructions to keep future contributions consistent.
- Rationale: Mirrored structure improves discoverability, code-to-test traceability, and maintenance as the codebase grows.