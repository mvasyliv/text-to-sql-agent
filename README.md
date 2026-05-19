# Text-to-SQL Agent

## Team Git Standard

Branch naming: type/T-YYYY-MM-DD-NNN-short-slug (one task = one branch).

Commit message: type(scope): short summary [T-YYYY-MM-DD-NNN].

PR title: type: short summary [T-YYYY-MM-DD-NNN]; merge to main only via PR.

## Query Graph (Current)

![Current query orchestration graph](docs/query_graph.png)

Comment: this diagram reflects the current `build_query_graph()` flow, including conditional branches to `failed` and the human-approval interrupt point.
