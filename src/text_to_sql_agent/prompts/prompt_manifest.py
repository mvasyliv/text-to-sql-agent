"""Prompt manifest contracts for MVP and enterprise SQL prompt rollout."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .dialect_scope import DialectName, list_supported_dialects


RolloutStrategy = Literal["off", "canary", "full"]
ManifestStatus = Literal["draft", "active"]
RolloutPolicyLevel = Literal["low_risk", "standard", "strict"]
ApprovalStatus = Literal["pending", "approved", "rejected"]
TenantIsolationMode = Literal["single_tenant", "tenant_allowlist"]


class PromptRollout(BaseModel):
    """Basic rollout control for a prompt manifest."""

    strategy: RolloutStrategy = Field(
        default="off", description="Rollout mode for this prompt version"
    )
    percentage: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Traffic percentage routed to this prompt version",
    )

    @model_validator(mode="after")
    def validate_strategy_percentage(self) -> "PromptRollout":
        if self.strategy == "off" and self.percentage != 0:
            raise ValueError("Rollout strategy 'off' requires percentage=0")
        if self.strategy == "full" and self.percentage != 100:
            raise ValueError("Rollout strategy 'full' requires percentage=100")
        if self.strategy == "canary" and not (1 <= self.percentage <= 99):
            raise ValueError("Rollout strategy 'canary' requires percentage in 1..99")
        return self


class PromptManifestMVP(BaseModel):
    """Minimal manifest fields for read-only SQL generation in MVP."""

    manifest_id: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[a-zA-Z0-9._:-]+$",
        description="Stable prompt identifier",
    )
    version: int = Field(ge=1, description="Monotonic prompt version")
    dialect: DialectName = Field(description="Target SQL dialect")
    status: ManifestStatus = Field(default="draft")
    owner: str = Field(min_length=1, max_length=128)
    prompt_template: str = Field(
        min_length=20,
        description="Prompt template text. Must include required placeholders.",
    )
    read_only_required: bool = Field(
        default=True, description="MVP hard requirement for safe read-only generation"
    )
    max_limit: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Hard upper bound for generated LIMIT",
    )
    rollout: PromptRollout = Field(default_factory=PromptRollout)
    required_guardrails: tuple[str, ...] = Field(
        default=(
            "single_statement",
            "select_or_with_only",
            "enforce_limit",
            "deny_dml_ddl",
        )
    )
    disallowed_operations: tuple[str, ...] = Field(
        default=(
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "ALTER",
            "TRUNCATE",
            "MERGE",
            "GRANT",
            "REVOKE",
            "CREATE",
        )
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("prompt_template")
    @classmethod
    def validate_prompt_template_placeholders(cls, value: str) -> str:
        required = ("{user_request}", "{schema_context}")
        missing = [token for token in required if token not in value]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Prompt template missing required placeholders: {joined}")
        return value

    @field_validator("disallowed_operations")
    @classmethod
    def validate_disallowed_operations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip().upper() for item in value if item.strip())
        if len(set(normalized)) != len(normalized):
            raise ValueError("disallowed_operations contains duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_mvp_contract(self) -> "PromptManifestMVP":
        if not self.read_only_required:
            raise ValueError("MVP manifest requires read_only_required=True")

        if self.status == "active" and self.rollout.strategy == "off":
            raise ValueError("Active manifest must have rollout strategy canary or full")

        if "select_or_with_only" not in self.required_guardrails:
            raise ValueError("required_guardrails must include 'select_or_with_only'")

        if self.dialect not in list_supported_dialects():
            supported = ", ".join(list_supported_dialects())
            raise ValueError(f"Unsupported dialect '{self.dialect}'. Supported: {supported}")

        return self


class TenantIsolationPolicy(BaseModel):
    """Tenant isolation controls for enterprise prompt manifests."""

    mode: TenantIsolationMode = Field(default="single_tenant")
    tenant_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9._:-]+$",
        description="Primary tenant identifier",
    )
    allowed_tenant_ids: tuple[str, ...] = Field(
        default=(),
        description="Optional tenant allowlist for shared prompt variants",
    )

    @field_validator("allowed_tenant_ids")
    @classmethod
    def normalize_allowed_tenants(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        if len(set(normalized)) != len(normalized):
            raise ValueError("allowed_tenant_ids contains duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_tenant_mode(self) -> "TenantIsolationPolicy":
        if self.mode == "single_tenant" and self.allowed_tenant_ids:
            raise ValueError("single_tenant mode does not allow allowed_tenant_ids")
        if self.mode == "tenant_allowlist" and self.tenant_id not in self.allowed_tenant_ids:
            raise ValueError(
                "tenant_allowlist mode requires tenant_id to be included in allowed_tenant_ids"
            )
        return self


class PromptAuditMetadata(BaseModel):
    """Audit metadata required for enterprise prompt governance."""

    created_by: str = Field(min_length=1, max_length=128)
    updated_by: str = Field(min_length=1, max_length=128)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    change_ticket: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[A-Z]+-[0-9]+$",
        description="Change request ticket identifier",
    )
    checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
        description="SHA-256 checksum for prompt template integrity",
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> "PromptAuditMetadata":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self


class PromptApprovalMetadata(BaseModel):
    """Approval metadata required before enterprise activation."""

    status: ApprovalStatus = Field(default="pending")
    required_reviewers: tuple[str, ...] = Field(default=("security", "data-platform"))
    approved_by: str | None = Field(default=None, max_length=128)
    approved_at: datetime | None = None
    policy_level: RolloutPolicyLevel = Field(default="standard")

    @field_validator("required_reviewers")
    @classmethod
    def validate_required_reviewers(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        if not normalized:
            raise ValueError("required_reviewers must contain at least one reviewer")
        if len(set(normalized)) != len(normalized):
            raise ValueError("required_reviewers contains duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_approval_consistency(self) -> "PromptApprovalMetadata":
        if self.status == "approved":
            if not self.approved_by or self.approved_at is None:
                raise ValueError("approved status requires approved_by and approved_at")
        else:
            if self.approved_by or self.approved_at is not None:
                raise ValueError(
                    "approved_by and approved_at are allowed only when status='approved'"
                )
        return self


class PromptManifestEnterprise(PromptManifestMVP):
    """Enterprise manifest with tenant isolation and audit governance."""

    environment: Literal["dev", "staging", "prod"] = Field(default="staging")
    tenant_policy: TenantIsolationPolicy
    audit: PromptAuditMetadata
    approval: PromptApprovalMetadata
    compliance_tags: tuple[str, ...] = Field(default=("sox", "audit-log"))

    @field_validator("compliance_tags")
    @classmethod
    def validate_compliance_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip().lower() for item in value if item.strip())
        if not normalized:
            raise ValueError("compliance_tags must contain at least one tag")
        if len(set(normalized)) != len(normalized):
            raise ValueError("compliance_tags contains duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_enterprise_contract(self) -> "PromptManifestEnterprise":
        if self.status == "active" and self.approval.status != "approved":
            raise ValueError("Active enterprise manifest requires approval.status='approved'")

        if self.status == "active" and self.environment == "prod":
            if self.approval.policy_level == "strict":
                if self.rollout.strategy != "canary":
                    raise ValueError(
                        "Strict policy in prod requires canary rollout before full rollout"
                    )
                if self.rollout.percentage > 25:
                    raise ValueError(
                        "Strict policy in prod requires canary percentage <= 25"
                    )

            if self.approval.policy_level == "standard" and self.rollout.strategy == "off":
                raise ValueError("Standard policy in prod cannot use rollout strategy 'off'")

        return self


def build_mvp_manifest(
    manifest_id: str,
    version: int,
    dialect: DialectName,
    owner: str,
    prompt_template: str,
    *,
    status: ManifestStatus = "draft",
    rollout: PromptRollout | None = None,
) -> PromptManifestMVP:
    """Build a validated MVP prompt manifest."""
    return PromptManifestMVP(
        manifest_id=manifest_id,
        version=version,
        dialect=dialect,
        status=status,
        owner=owner,
        prompt_template=prompt_template,
        rollout=rollout or PromptRollout(),
    )


def build_enterprise_manifest(
    manifest_id: str,
    version: int,
    dialect: DialectName,
    owner: str,
    prompt_template: str,
    tenant_policy: TenantIsolationPolicy,
    audit: PromptAuditMetadata,
    approval: PromptApprovalMetadata,
    *,
    status: ManifestStatus = "draft",
    rollout: PromptRollout | None = None,
    environment: Literal["dev", "staging", "prod"] = "staging",
) -> PromptManifestEnterprise:
    """Build a validated enterprise prompt manifest."""
    return PromptManifestEnterprise(
        manifest_id=manifest_id,
        version=version,
        dialect=dialect,
        status=status,
        owner=owner,
        prompt_template=prompt_template,
        rollout=rollout or PromptRollout(),
        environment=environment,
        tenant_policy=tenant_policy,
        audit=audit,
        approval=approval,
    )
