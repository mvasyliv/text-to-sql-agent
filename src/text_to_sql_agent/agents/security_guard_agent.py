"""SQL security guard agent for MVP query pipeline.

This validator enforces read-only execution policy and blocks suspicious SQL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from text_to_sql_agent.services.audit_trail import make_agent_event
from text_to_sql_agent.services.mcp_security_policy import validate_mcp_sql_policy


_DISALLOWED_OPERATIONS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "merge",
    "grant",
    "revoke",
    "create",
    "replace",
)

_SUSPICIOUS_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"--"), "inline_comment"),
    (re.compile(r"/\*"), "block_comment"),
    (re.compile(r"\bunion\s+select\b", re.IGNORECASE), "union_select"),
    (re.compile(r"\bor\s+1\s*=\s*1\b", re.IGNORECASE), "tautology_or_1_eq_1"),
)


@dataclass(frozen=True, slots=True)
class SQLSecurityValidationResult:
    """Result of SQL security validation."""

    approved: bool
    violations: list[str]


def _starts_read_only(sql: str) -> bool:
    first = sql.lstrip().split(maxsplit=1)[0].lower() if sql.strip() else ""
    return first in {"select", "with"}


def _contains_disallowed_operation(sql: str) -> str | None:
    for keyword in _DISALLOWED_OPERATIONS:
        if re.search(rf"\b{re.escape(keyword)}\b", sql, flags=re.IGNORECASE):
            return keyword
    return None


def _contains_suspicious_pattern(sql: str) -> list[str]:
    matches: list[str] = []
    for pattern, label in _SUSPICIOUS_PATTERNS:
        if pattern.search(sql):
            matches.append(label)
    return matches


def validate_sql_security(sql: str) -> SQLSecurityValidationResult:
    """Validate SQL against read-only and suspicious-pattern constraints."""
    if not isinstance(sql, str):
        raise TypeError("SQL must be a string")

    normalized = sql.strip()
    policy_result = validate_mcp_sql_policy(normalized)
    violations: list[str] = []

    for violation in policy_result.violations:
        if violation.startswith("denied_operation:"):
            violations.append(violation.split(":", maxsplit=1)[1])
        else:
            violations.append(violation)

    violations.extend(_contains_suspicious_pattern(normalized))

    return SQLSecurityValidationResult(
        approved=(len(violations) == 0),
        violations=violations,
    )


def build_security_guard_node():
    """Return a LangGraph-compatible security guard node."""

    def node(state: dict) -> dict:
        sql = state.get("edited_sql") or state.get("generated_sql") or ""
        try:
            result = validate_sql_security(sql)
            return {
                "security_approved": result.approved,
                "security_violations": result.violations,
                "status": "awaiting_approval" if result.approved else "failed",
                "log_messages": [
                    "security_guard: "
                    f"approved={result.approved}, violations={result.violations}"
                ],
                "agent_events": [
                    make_agent_event(
                        agent="security_guard",
                        event_type="security_checked",
                        status="ok" if result.approved else "error",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"approved": result.approved, "violations": result.violations},
                    )
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "security_approved": False,
                "security_violations": [str(exc)],
                "status": "failed",
                "error_message": f"security_guard: failed - {exc}",
                "log_messages": [f"security_guard: ERROR - {exc}"],
                "agent_events": [
                    make_agent_event(
                        agent="security_guard",
                        event_type="security_checked",
                        status="error",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"error": str(exc)},
                    )
                ],
            }

    return node
