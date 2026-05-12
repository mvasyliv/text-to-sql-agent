"""Tests for prompt storage and version registry contract."""

from datetime import datetime, timezone

import pytest

from text_to_sql_agent.prompts.storage_registry import (
    PromptOwnership,
    PromptStorageConfig,
    PromptVersionRecord,
    PromptVersionRegistry,
    build_prompt_version_registry,
)


def make_record(version: int, status: str) -> PromptVersionRecord:
    now = datetime.now(timezone.utc)
    return PromptVersionRecord(
        manifest_id="mvp.sales.monthly",
        version=version,
        status=status,
        checksum_sha256="a" * 64,
        template_uri=f"s3://prompt-bucket/prompts/mvp.sales.monthly/v{version}.txt",
        ownership=PromptOwnership(
            owner_type="team",
            owner_id="prompt-team",
            contact_channel="#prompt-governance",
        ),
        created_at=now,
        updated_at=now,
        created_by="dev-a",
        updated_by="dev-a",
    )


def test_build_registry_with_valid_pointers() -> None:
    registry = build_prompt_version_registry(
        manifest_id="mvp.sales.monthly",
        storage=PromptStorageConfig(
            backend="s3",
            bucket_or_container="prompt-bucket",
            namespace="text-to-sql",
            object_key_prefix="prompts/",
            region="eu-west-1",
        ),
        versions=(
            make_record(1, "retired"),
            make_record(2, "canary"),
            make_record(3, "active"),
        ),
        active_version=3,
        canary_version=2,
    )

    assert registry.latest_version == 3
    assert registry.active_version == 3
    assert registry.canary_version == 2


def test_latest_version_is_required_when_versions_exist() -> None:
    with pytest.raises(ValueError, match="latest_version"):
        PromptVersionRegistry(
            manifest_id="mvp.sales.monthly",
            storage=PromptStorageConfig(
                backend="filesystem",
                bucket_or_container="/tmp",
                namespace="text-to-sql",
            ),
            versions=(make_record(1, "active"),),
            latest_version=None,
            active_version=1,
        )


def test_active_pointer_requires_active_status() -> None:
    with pytest.raises(ValueError, match="status='active'"):
        build_prompt_version_registry(
            manifest_id="mvp.sales.monthly",
            storage=PromptStorageConfig(
                backend="s3",
                bucket_or_container="prompt-bucket",
                namespace="text-to-sql",
            ),
            versions=(
                make_record(1, "approved"),
                make_record(2, "canary"),
            ),
            active_version=1,
            canary_version=2,
        )


def test_canary_pointer_requires_canary_status() -> None:
    with pytest.raises(ValueError, match="status='canary'"):
        build_prompt_version_registry(
            manifest_id="mvp.sales.monthly",
            storage=PromptStorageConfig(
                backend="s3",
                bucket_or_container="prompt-bucket",
                namespace="text-to-sql",
            ),
            versions=(
                make_record(1, "active"),
                make_record(2, "approved"),
            ),
            active_version=1,
            canary_version=2,
        )


def test_template_uri_scheme_is_validated() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="template_uri"):
        PromptVersionRecord(
            manifest_id="mvp.sales.monthly",
            version=1,
            status="draft",
            checksum_sha256="b" * 64,
            template_uri="https://example.com/prompt.txt",
            ownership=PromptOwnership(
                owner_type="team",
                owner_id="prompt-team",
                contact_channel="#prompt-governance",
            ),
            created_at=now,
            updated_at=now,
            created_by="dev-a",
            updated_by="dev-a",
        )
