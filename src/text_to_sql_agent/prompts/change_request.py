"""Prompt change request contract for governed prompt updates."""

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ChangeRequestType = Literal["standard", "emergency_hotfix"]
ChangeRequestStatus = Literal[
    "draft",
    "submitted",
    "in_review",
    "approved",
    "rejected",
    "implemented",
    "postmortem_required",
    "closed",
]
ApprovalDecision = Literal["approved", "rejected"]


class PromptChangeApproval(BaseModel):
    """Single approval record for a prompt change request."""

    role: str = Field(min_length=1, max_length=128)
    approver: str = Field(min_length=1, max_length=128)
    decision: ApprovalDecision = Field(default="approved")
    approved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    comment: str | None = Field(default=None, max_length=1000)


class PromptChangeRequest(BaseModel):
    """Governed process contract for prompt updates."""

    request_id: str = Field(
        pattern=r"^CRQ-[0-9]{8}-[0-9]{3}$",
        description="Change request id, for example CRQ-20260512-001",
    )
    change_type: ChangeRequestType = Field(default="standard")
    status: ChangeRequestStatus = Field(default="draft")
    manifest_id: str = Field(min_length=3, max_length=128)
    current_version: int = Field(ge=1)
    proposed_version: int = Field(ge=1)
    requested_by: str = Field(min_length=1, max_length=128)
    owner: str = Field(min_length=1, max_length=128)
    summary: str = Field(min_length=10, max_length=500)
    rationale: str = Field(min_length=20, max_length=2000)
    risk_assessment: str = Field(min_length=20, max_length=2000)
    test_evidence: str = Field(min_length=10, max_length=2000)
    rollback_plan: str = Field(min_length=20, max_length=2000)
    approvers_required: tuple[str, ...] = Field(
        default=("prompt-owner", "data-platform", "security"),
        description="Roles required for standard change approval",
    )
    approvals: tuple[PromptChangeApproval, ...] = Field(default=())
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Emergency hotfix path
    incident_id: str | None = Field(default=None, pattern=r"^INC-[0-9]+$")
    expedited_approved_by: tuple[str, ...] = Field(default=())
    postmortem_due_at: datetime | None = None
    postmortem_completed_at: datetime | None = None

    @field_validator("approvers_required")
    @classmethod
    def validate_approvers_required(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip().lower() for item in value if item.strip())
        if not normalized:
            raise ValueError("approvers_required must include at least one role")
        if len(set(normalized)) != len(normalized):
            raise ValueError("approvers_required contains duplicates")
        return normalized

    @field_validator("expedited_approved_by")
    @classmethod
    def validate_expedited_approvers(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        if len(set(normalized)) != len(normalized):
            raise ValueError("expedited_approved_by contains duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_contract(self) -> "PromptChangeRequest":
        if self.proposed_version <= self.current_version:
            raise ValueError("proposed_version must be greater than current_version")

        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")

        approved_roles = {
            approval.role.strip().lower()
            for approval in self.approvals
            if approval.decision == "approved"
        }

        approval_gate_statuses = {"approved", "implemented", "closed"}

        if self.change_type == "standard":
            if self.incident_id or self.expedited_approved_by:
                raise ValueError(
                    "incident_id and expedited_approved_by are only for emergency_hotfix"
                )
            if self.postmortem_due_at or self.postmortem_completed_at:
                raise ValueError(
                    "postmortem fields are only for emergency_hotfix requests"
                )

            if self.status in approval_gate_statuses:
                missing_roles = [
                    role for role in self.approvers_required if role not in approved_roles
                ]
                if missing_roles:
                    missing = ", ".join(missing_roles)
                    raise ValueError(
                        f"standard request missing required approvals for roles: {missing}"
                    )

        if self.change_type == "emergency_hotfix":
            if not self.incident_id:
                raise ValueError("emergency_hotfix requires incident_id")
            if len(self.expedited_approved_by) < 2:
                raise ValueError(
                    "emergency_hotfix requires at least two expedited approvers"
                )
            if self.postmortem_due_at is None:
                raise ValueError("emergency_hotfix requires postmortem_due_at")
            if self.postmortem_due_at > self.created_at + timedelta(days=3):
                raise ValueError(
                    "postmortem_due_at must be within 72 hours of request creation"
                )

            if self.status == "closed" and self.postmortem_completed_at is None:
                raise ValueError(
                    "emergency_hotfix closed status requires postmortem_completed_at"
                )

            if self.postmortem_completed_at and self.postmortem_completed_at < self.created_at:
                raise ValueError(
                    "postmortem_completed_at cannot be earlier than created_at"
                )

        return self


def build_prompt_change_request(
    request_id: str,
    manifest_id: str,
    current_version: int,
    proposed_version: int,
    requested_by: str,
    owner: str,
    summary: str,
    rationale: str,
    risk_assessment: str,
    test_evidence: str,
    rollback_plan: str,
    *,
    change_type: ChangeRequestType = "standard",
    status: ChangeRequestStatus = "draft",
) -> PromptChangeRequest:
    """Build a validated prompt change request object."""
    return PromptChangeRequest(
        request_id=request_id,
        change_type=change_type,
        status=status,
        manifest_id=manifest_id,
        current_version=current_version,
        proposed_version=proposed_version,
        requested_by=requested_by,
        owner=owner,
        summary=summary,
        rationale=rationale,
        risk_assessment=risk_assessment,
        test_evidence=test_evidence,
        rollback_plan=rollback_plan,
    )
