"""Tests for enterprise prompt manifest contract."""

from datetime import datetime, timedelta, timezone

import pytest

from text_to_sql_agent.prompts.prompt_manifest import (
    PromptApprovalMetadata,
    PromptAuditMetadata,
    PromptRollout,
    TenantIsolationPolicy,
    build_enterprise_manifest,
)


VALID_TEMPLATE = (
    "You are a SQL generator.\n"
    "Question: {user_request}\n"
    "Schema: {schema_context}\n"
    "Return one read-only SQL query."
)


def build_valid_audit() -> PromptAuditMetadata:
    now = datetime.now(timezone.utc)
    return PromptAuditMetadata(
        created_by="developer-a",
        updated_by="developer-a",
        created_at=now,
        updated_at=now,
        change_ticket="DATA-123",
        checksum_sha256="a" * 64,
    )


def build_valid_approval() -> PromptApprovalMetadata:
    return PromptApprovalMetadata(
        status="approved",
        required_reviewers=("security", "data-platform"),
        approved_by="approver-a",
        approved_at=datetime.now(timezone.utc),
        policy_level="standard",
    )


def test_build_enterprise_manifest_valid_active_prod_canary() -> None:
    manifest = build_enterprise_manifest(
        manifest_id="ent.sales.monthly",
        version=3,
        dialect="postgresql",
        owner="platform-team",
        prompt_template=VALID_TEMPLATE,
        status="active",
        environment="prod",
        rollout=PromptRollout(strategy="canary", percentage=20),
        tenant_policy=TenantIsolationPolicy(mode="single_tenant", tenant_id="tenant-a"),
        audit=build_valid_audit(),
        approval=build_valid_approval(),
    )

    assert manifest.environment == "prod"
    assert manifest.approval.status == "approved"
    assert manifest.tenant_policy.tenant_id == "tenant-a"


def test_tenant_allowlist_requires_primary_tenant_in_list() -> None:
    with pytest.raises(ValueError, match="requires tenant_id to be included"):
        TenantIsolationPolicy(
            mode="tenant_allowlist",
            tenant_id="tenant-a",
            allowed_tenant_ids=("tenant-b", "tenant-c"),
        )


def test_single_tenant_mode_disallows_allowlist() -> None:
    with pytest.raises(ValueError, match="single_tenant mode"):
        TenantIsolationPolicy(
            mode="single_tenant",
            tenant_id="tenant-a",
            allowed_tenant_ids=("tenant-a",),
        )


def test_audit_updated_at_cannot_be_earlier_than_created_at() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="updated_at cannot be earlier"):
        PromptAuditMetadata(
            created_by="developer-a",
            updated_by="developer-a",
            created_at=now,
            updated_at=now - timedelta(minutes=5),
            change_ticket="DATA-123",
            checksum_sha256="b" * 64,
        )


def test_approved_status_requires_approval_metadata() -> None:
    with pytest.raises(ValueError, match="requires approved_by and approved_at"):
        PromptApprovalMetadata(status="approved", required_reviewers=("security",))


def test_active_enterprise_manifest_requires_approved_status() -> None:
    with pytest.raises(ValueError, match="requires approval.status='approved'"):
        build_enterprise_manifest(
            manifest_id="ent.sales.monthly",
            version=3,
            dialect="postgresql",
            owner="platform-team",
            prompt_template=VALID_TEMPLATE,
            status="active",
            environment="staging",
            rollout=PromptRollout(strategy="canary", percentage=10),
            tenant_policy=TenantIsolationPolicy(mode="single_tenant", tenant_id="tenant-a"),
            audit=build_valid_audit(),
            approval=PromptApprovalMetadata(status="pending", required_reviewers=("security",)),
        )


def test_strict_policy_in_prod_requires_canary_up_to_25_percent() -> None:
    approval = PromptApprovalMetadata(
        status="approved",
        required_reviewers=("security",),
        approved_by="approver-a",
        approved_at=datetime.now(timezone.utc),
        policy_level="strict",
    )

    with pytest.raises(ValueError, match="requires canary rollout"):
        build_enterprise_manifest(
            manifest_id="ent.sales.monthly",
            version=3,
            dialect="postgresql",
            owner="platform-team",
            prompt_template=VALID_TEMPLATE,
            status="active",
            environment="prod",
            rollout=PromptRollout(strategy="full", percentage=100),
            tenant_policy=TenantIsolationPolicy(mode="single_tenant", tenant_id="tenant-a"),
            audit=build_valid_audit(),
            approval=approval,
        )

    with pytest.raises(ValueError, match="percentage <= 25"):
        build_enterprise_manifest(
            manifest_id="ent.sales.monthly",
            version=3,
            dialect="postgresql",
            owner="platform-team",
            prompt_template=VALID_TEMPLATE,
            status="active",
            environment="prod",
            rollout=PromptRollout(strategy="canary", percentage=40),
            tenant_policy=TenantIsolationPolicy(mode="single_tenant", tenant_id="tenant-a"),
            audit=build_valid_audit(),
            approval=approval,
        )
