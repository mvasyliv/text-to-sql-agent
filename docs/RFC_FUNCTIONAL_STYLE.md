# RFC: Incremental Functional-Style Migration

- Status: Draft
- Date: 2026-05-29
- Related task: `T-2026-05-29-086`

## Summary

This RFC defines how the repository applies a functional-first style to core business logic without rewriting the whole system.

The target architecture is **functional core, imperative shell**:

- keep pure, deterministic transformation logic in the core
- keep I/O, framework callbacks, persistence, and process/runtime interactions at the boundaries
- migrate incrementally through small, reviewable PRs

## Motivation

The current codebase already has several places where deterministic logic can be isolated from UI and repository concerns.

A project-specific RFC is needed so contributors share the same answers to these questions:

- what counts as "functional style" in this repository
- where it is expected by default
- what is explicitly out of scope
- how migration work should be phased and reviewed

## Scope

Functional style is the default for:

- `src/text_to_sql_agent/services/`
- pure transformation logic inside `src/text_to_sql_agent/agents/`
- reusable data-shaping utilities in `src/text_to_sql_agent/utils/`

In these areas, preferred patterns are:

- pure functions with explicit inputs and outputs
- immutable or effectively immutable return values where practical
- deterministic transformations
- injected dependencies instead of hidden lookups
- narrow wrappers around side-effecting integrations

## Boundary Layers

Imperative style is expected and acceptable in:

- `src/text_to_sql_agent/ui/`
- `src/text_to_sql_agent/repositories/`
- runtime entrypoints such as `main.py`, `main_chainlit.py`, and `main_terminal.py`

These layers may:

- call framework APIs
- perform database, file, or network I/O
- manage sessions, callbacks, and process environment
- translate between framework objects and internal typed models

## Non-Goals

This RFC does not require:

- a full rewrite of existing modules
- removal of all classes
- banning dataclasses or Pydantic models
- converting boundary code into artificial pure abstractions
- changing stable public APIs without a separate need

## Migration Rules

When touching code in scope:

1. Prefer extracting pure derivation/building logic before changing behavior.
2. Keep existing external APIs stable when possible.
3. Introduce thin wrappers when callers still expect the old service shape.
4. Add focused tests for the extracted pure layer.
5. Avoid mixing new side effects into the extracted core.

## Recommended Refactor Pattern

Use this sequence for incremental work:

1. identify deterministic logic inside an existing module
2. extract it into a dedicated pure helper module or clearly isolated pure functions
3. keep the existing service/adapter module as a thin wrapper
4. add focused tests for the pure layer
5. keep broader integration tests where they already exist

## Pilot Modules

The first pilot modules are:

- `src/text_to_sql_agent/ui/renderers.py`
- `src/text_to_sql_agent/services/query_analytics.py`
- `src/text_to_sql_agent/services/query_insights.py`

These are good pilots because they contain deterministic transformation logic with limited boundary risk.

## Rollout Criteria

A migration PR is considered aligned with this RFC when:

- the functional boundary is explicit in code structure
- the pure layer has focused deterministic tests
- the wrapper or boundary layer remains small and readable
- no new hidden side effects are introduced into core logic
- existing callers continue to work without unnecessary API churn

## Review Standard

All functional-style PRs should be reviewed with:

- `docs/FUNCTIONAL_STYLE_REVIEW_CHECKLIST.md`
- `.github/PULL_REQUEST_TEMPLATE.md`

## Current Applied Examples

As of this RFC, the following modules already follow the intended pattern:

- `src/text_to_sql_agent/ui/render_models.py` extracted from UI renderers
- `src/text_to_sql_agent/services/query_analytics_derivation.py`
- `src/text_to_sql_agent/services/query_insights_derivation.py`

## Risks and Mitigations

### Risk: over-abstraction

Mitigation:
- only extract logic that is clearly deterministic and reusable
- prefer small modules over generic frameworks

### Risk: API churn

Mitigation:
- preserve wrapper APIs where practical
- separate structural refactors from behavior changes

### Risk: mixed styles inside one file

Mitigation:
- keep imperative glue thin
- move pure logic into dedicated modules when it grows beyond a few helper functions

## Proposed Adoption

This RFC is the draft reference for future functional-style refactors and can be refined as additional migration examples are completed.

