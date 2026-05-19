"""Tests for human approval gate agent (T-2026-05-18-046)."""

from text_to_sql_agent.agents.human_approval_agent import (
    HumanApprovalDecision,
    build_human_approval_node,
    normalize_approval_decision,
)


class TestNormalizeApprovalDecision:
    def test_normalize_approve(self):
        result = normalize_approval_decision("approve")
        assert result == HumanApprovalDecision(action="approve", edited_sql=None)

    def test_normalize_cancel_alias(self):
        result = normalize_approval_decision("cancel")
        assert result.action == "cancel"

    def test_normalize_reject(self):
        result = normalize_approval_decision("reject")
        assert result.action == "cancel"

    def test_normalize_edit(self):
        result = normalize_approval_decision({"edit": "SELECT id FROM users"})
        assert result.action == "edit"
        assert result.edited_sql == "SELECT id FROM users"

    def test_normalize_empty_edit_becomes_reject(self):
        result = normalize_approval_decision({"edit": "   "})
        assert result.action == "reject"

    def test_normalize_unknown_becomes_reject(self):
        result = normalize_approval_decision({"unexpected": True})
        assert result.action == "reject"


class TestBuildHumanApprovalNode:
    def _state(self):
        return {
            "generated_sql": "SELECT * FROM users LIMIT 10",
            "edited_sql": None,
        }

    def test_node_approve(self):
        node = build_human_approval_node(interrupt_fn=lambda _: "approve")
        result = node(self._state())

        assert result["human_approved"] is True
        assert result["status"] == "executing"
        assert "approved" in result["log_messages"][0]

    def test_node_reject(self):
        node = build_human_approval_node(interrupt_fn=lambda _: "reject")
        result = node(self._state())

        assert result["human_approved"] is False
        assert result["status"] == "cancelled"

    def test_node_edit(self):
        node = build_human_approval_node(
            interrupt_fn=lambda _: {"edit": "SELECT id, name FROM users LIMIT 5"}
        )
        result = node(self._state())

        assert result["human_approved"] is True
        assert result["status"] == "executing"
        assert result["edited_sql"] == "SELECT id, name FROM users LIMIT 5"
