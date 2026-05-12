"""Tests for prompt change request process contract."""

from datetime import datetime, timedelta, timezone

import pytest

from text_to_sql_agent.prompts.change_request import (
    PromptChangeApproval,
    PromptChangeRequest,
    build_prompt_change_request,
)


def test_build_standard_change_request_defaults() -> None:
    request = build_prompt_change_request(
        request_id="CRQ-20260512-001",
        manifest_id="mvp.sales.monthly",
        current_version=1,
        proposed_version=2,
        requested_by="dev-a",
        owner="prompt-team",
        summary="Tune prompt for better join disambiguation",
        rationale="Recent failures show incorrect join key selection in monthly analytics queries.",
        risk_assessment="Low to medium risk because behavior remains read-only and constrained.",
        test_evidence="Validated with 50 prompt regression cases and no destructive SQL generation.",
        rollback_plan="Rollback by restoring version 1 and setting rollout strategy to off.",
    )

    assert request.change_type == "standard"
    assert request.status == "draft"
    assert request.approvers_required == ("prompt-owner", "data-platform", "security")


def test_standard_approved_status_requires_all_role_approvals() -> None:
    with pytest.raises(ValueError, match="missing required approvals"):
        PromptChangeRequest(
            request_id="CRQ-20260512-002",
            change_type="standard",
            status="approved",
            manifest_id="mvp.sales.monthly",
            current_version=1,
            proposed_version=2,
            requested_by="dev-a",
            owner="prompt-team",
            summary="Tune prompt for better aggregation behavior",
            rationale="Detected aggregation ambiguity in grouped output for edge cases.",
            risk_assessment="Medium risk because query wording changes may affect generated SQL shape.",
            test_evidence="Regression set executed in staging without runtime errors.",
            rollback_plan="Revert to previous prompt manifest version and redeploy.",
            approvals=(
                PromptChangeApproval(role="prompt-owner", approver="owner-a"),
                PromptChangeApproval(role="security", approver="sec-a"),
            ),
        )


def test_standard_approved_status_with_all_roles_is_valid() -> None:
    request = PromptChangeRequest(
        request_id="CRQ-20260512-003",
        change_type="standard",
        status="approved",
        manifest_id="mvp.sales.monthly",
        current_version=1,
        proposed_version=2,
        requested_by="dev-a",
        owner="prompt-team",
        summary="Tune prompt for dialect-specific date bucketing",
        rationale="Need clearer hints for PostgreSQL and Athena monthly bucket generation.",
        risk_assessment="Low risk due to narrow template text changes and existing guards.",
        test_evidence="Staging validation passed across all supported dialect fixtures.",
        rollback_plan="Re-enable previous version through manifest promotion rollback.",
        approvals=(
            PromptChangeApproval(role="prompt-owner", approver="owner-a"),
            PromptChangeApproval(role="data-platform", approver="platform-a"),
            PromptChangeApproval(role="security", approver="sec-a"),
        ),
    )
    assert request.status == "approved"


def test_hotfix_requires_incident_expedited_approvers_and_postmortem_due() -> None:
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="requires incident_id"):
        PromptChangeRequest(
            request_id="CRQ-20260512-004",
            change_type="emergency_hotfix",
            status="submitted",
            manifest_id="ent.sales.monthly",
            current_version=9,
            proposed_version=10,
            requested_by="oncall-a",
            owner="prompt-team",
            summary="Emergency fix for invalid SQL generation in production",
            rationale="Production incident shows failing queries due to malformed table aliases.",
            risk_assessment="High urgency and high risk until fix is deployed.",
            test_evidence="Smoke tests only due to incident severity.",
            rollback_plan="Immediately revert to previous active prompt if anomalies persist.",
            created_at=now,
            updated_at=now,
            expedited_approved_by=("oncall-lead", "security-oncall"),
            postmortem_due_at=now + timedelta(hours=24),
        )


def test_hotfix_closed_requires_postmortem_completed() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="requires postmortem_completed_at"):
        PromptChangeRequest(
            request_id="CRQ-20260512-005",
            change_type="emergency_hotfix",
            status="closed",
            manifest_id="ent.sales.monthly",
            current_version=9,
            proposed_version=10,
            requested_by="oncall-a",
            owner="prompt-team",
            summary="Emergency fix for malformed SQL limit clause",
            rationale="Incident indicates malformed LIMIT rendering in production requests.",
            risk_assessment="High risk due to production impact and urgent deployment.",
            test_evidence="Smoke tests and one rollback drill completed.",
            rollback_plan="Restore previous prompt version and freeze rollouts.",
            created_at=now,
            updated_at=now,
            incident_id="INC-12345",
            expedited_approved_by=("oncall-lead", "security-oncall"),
            postmortem_due_at=now + timedelta(hours=24),
        )


def test_hotfix_postmortem_due_within_72_hours() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="within 72 hours"):
        PromptChangeRequest(
            request_id="CRQ-20260512-006",
            change_type="emergency_hotfix",
            status="submitted",
            manifest_id="ent.sales.monthly",
            current_version=9,
            proposed_version=10,
            requested_by="oncall-a",
            owner="prompt-team",
            summary="Emergency mitigation for production prompt regression",
            rationale="Critical incident requires immediate patch and accelerated approval.",
            risk_assessment="High risk and high urgency due to customer-facing errors.",
            test_evidence="Targeted incident reproduction and smoke validation.",
            rollback_plan="Rollback to previous enterprise manifest version.",
            created_at=now,
            updated_at=now,
            incident_id="INC-12346",
            expedited_approved_by=("oncall-lead", "security-oncall"),
            postmortem_due_at=now + timedelta(days=4),
        )


def test_proposed_version_must_increase() -> None:
    with pytest.raises(ValueError, match="greater than current_version"):
        build_prompt_change_request(
            request_id="CRQ-20260512-007",
            manifest_id="mvp.sales.monthly",
            current_version=2,
            proposed_version=2,
            requested_by="dev-a",
            owner="prompt-team",
            summary="No-op version update attempt",
            rationale="Attempted to submit without increasing version for governance testing.",
            risk_assessment="Low risk but invalid governance input.",
            test_evidence="Validation expected to fail.",
            rollback_plan="No rollback needed for rejected request.",
        )
