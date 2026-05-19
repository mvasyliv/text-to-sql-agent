"""Human approval gate agent for query execution workflow.

The gate requires explicit user confirmation before SQL execution and supports:
- approve: execute generated SQL
- reject/cancel: stop workflow
- edit: execute user-edited SQL
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from langgraph.types import interrupt

from text_to_sql_agent.services.audit_trail import make_agent_event


ApprovalAction = Literal["approve", "reject", "cancel", "edit"]


@dataclass(frozen=True, slots=True)
class HumanApprovalDecision:
    """Normalized decision extracted from resume payload."""

    action: ApprovalAction
    edited_sql: str | None = None


def normalize_approval_decision(decision: Any) -> HumanApprovalDecision:
    """Normalize resume payload into a strict approval decision model."""
    if isinstance(decision, dict) and "edit" in decision:
        edited = str(decision["edit"]).strip()
        if not edited:
            return HumanApprovalDecision(action="reject")
        return HumanApprovalDecision(action="edit", edited_sql=edited)

    if isinstance(decision, str):
        normalized = decision.strip().lower()
        if normalized == "approve":
            return HumanApprovalDecision(action="approve")
        if normalized in {"reject", "cancel"}:
            return HumanApprovalDecision(action="cancel")

    return HumanApprovalDecision(action="reject")


def build_human_approval_node(interrupt_fn=interrupt):
    """Return a LangGraph-compatible human approval node."""

    def node(state: dict) -> dict:
        sql = state.get("edited_sql") or state.get("generated_sql") or ""
        decision_payload = interrupt_fn(
            {
                "prompt": "Review the SQL query below and choose an action.",
                "sql": sql,
                "actions": ["approve", "reject", "edit"],
            }
        )
        decision = normalize_approval_decision(decision_payload)

        if decision.action == "edit":
            return {
                "human_approved": True,
                "edited_sql": decision.edited_sql,
                "status": "executing",
                "log_messages": ["human_approval: SQL edited and approved by user"],
                "agent_events": [
                    make_agent_event(
                        agent="human_approval",
                        event_type="human_approval",
                        status="ok",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"action": "edit"},
                    )
                ],
            }

        if decision.action == "approve":
            return {
                "human_approved": True,
                "status": "executing",
                "log_messages": ["human_approval: SQL approved by user"],
                "agent_events": [
                    make_agent_event(
                        agent="human_approval",
                        event_type="human_approval",
                        status="ok",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"action": "approve"},
                    )
                ],
            }

        return {
            "human_approved": False,
            "status": "cancelled",
            "log_messages": [
                "human_approval: rejected by user"
                f" (decision={decision_payload!r})"
            ],
            "agent_events": [
                make_agent_event(
                    agent="human_approval",
                    event_type="human_approval",
                    status="warning",
                    user_id=state.get("user_id"),
                    conversation_id=state.get("conversation_id"),
                    message_id=state.get("message_id"),
                    metadata={"action": decision.action},
                )
            ],
        }

    return node
