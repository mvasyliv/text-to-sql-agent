# Functional Style Review Checklist

Use this checklist when reviewing PRs that touch `src/text_to_sql_agent/services/`, pure transformation logic in `src/text_to_sql_agent/agents/`, or reusable helpers in `src/text_to_sql_agent/utils/`.

## Review Checklist

- [ ] Core logic is implemented as pure functions with explicit inputs and outputs.
- [ ] Side effects are isolated to the boundary layer (`ui`, `repositories`, or entrypoints).
- [ ] Dependencies are passed in explicitly; the core does not fetch hidden globals.
- [ ] Transformation steps are deterministic and easy to test without heavy mocking.
- [ ] Types and names make the data flow clear.
- [ ] Any intentional imperative step is small, localized, and justified.
- [ ] Tests cover the main path plus relevant edge cases and failure paths.

## Definition of Done

- [ ] The functional boundary is clear in code and review notes.
- [ ] The change does not leak I/O into core transformation logic.
- [ ] Tests and validation are updated for the changed behavior.
- [ ] `docs/TASKS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md`, and `docs/DECISIONS.md` are updated when the change affects process or project behavior.

