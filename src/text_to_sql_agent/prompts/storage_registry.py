"""Prompt storage and version registry contract."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


StorageBackend = Literal["s3", "azure_blob", "gcs", "postgres", "filesystem"]
VersionStatus = Literal["draft", "review", "approved", "canary", "active", "retired"]
OwnershipType = Literal["team", "user", "service-account"]


class PromptStorageConfig(BaseModel):
    """External prompt storage configuration."""

    backend: StorageBackend
    bucket_or_container: str = Field(min_length=1, max_length=256)
    namespace: str = Field(min_length=1, max_length=256)
    object_key_prefix: str = Field(default="prompts/")
    region: str | None = Field(default=None, max_length=64)


class PromptOwnership(BaseModel):
    """Ownership metadata for prompt governance."""

    owner_type: OwnershipType = Field(default="team")
    owner_id: str = Field(min_length=1, max_length=128)
    contact_channel: str = Field(min_length=3, max_length=256)


class PromptVersionRecord(BaseModel):
    """Single prompt version metadata in registry."""

    manifest_id: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[a-zA-Z0-9._:-]+$",
    )
    version: int = Field(ge=1)
    status: VersionStatus = Field(default="draft")
    checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    template_uri: str = Field(min_length=8, max_length=2048)
    ownership: PromptOwnership
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = Field(min_length=1, max_length=128)
    updated_by: str = Field(min_length=1, max_length=128)
    labels: tuple[str, ...] = Field(default=())

    @model_validator(mode="after")
    def validate_record(self) -> "PromptVersionRecord":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        if not self.template_uri.startswith(("s3://", "gs://", "az://", "file://")):
            raise ValueError(
                "template_uri must start with one of s3://, gs://, az://, file://"
            )
        return self


class PromptVersionRegistry(BaseModel):
    """Registry contract containing storage info and version pointers."""

    manifest_id: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[a-zA-Z0-9._:-]+$",
    )
    storage: PromptStorageConfig
    versions: tuple[PromptVersionRecord, ...] = Field(default=())
    active_version: int | None = None
    canary_version: int | None = None
    latest_version: int | None = None

    @model_validator(mode="after")
    def validate_registry(self) -> "PromptVersionRegistry":
        if not self.versions:
            if any(
                pointer is not None
                for pointer in (self.active_version, self.canary_version, self.latest_version)
            ):
                raise ValueError("version pointers must be None when versions list is empty")
            return self

        version_numbers = {record.version for record in self.versions}

        for record in self.versions:
            if record.manifest_id != self.manifest_id:
                raise ValueError("all version records must reference registry manifest_id")

        expected_latest = max(version_numbers)
        if self.latest_version is None:
            raise ValueError("latest_version is required when versions are present")
        if self.latest_version != expected_latest:
            raise ValueError("latest_version must be equal to highest version number")

        if self.active_version is not None and self.active_version not in version_numbers:
            raise ValueError("active_version must reference an existing version")
        if self.canary_version is not None and self.canary_version not in version_numbers:
            raise ValueError("canary_version must reference an existing version")

        if self.active_version is not None:
            active_record = next(
                record for record in self.versions if record.version == self.active_version
            )
            if active_record.status != "active":
                raise ValueError("active_version must point to a record with status='active'")

        if self.canary_version is not None:
            canary_record = next(
                record for record in self.versions if record.version == self.canary_version
            )
            if canary_record.status != "canary":
                raise ValueError("canary_version must point to a record with status='canary'")

        return self


def build_prompt_version_registry(
    manifest_id: str,
    storage: PromptStorageConfig,
    versions: tuple[PromptVersionRecord, ...],
    *,
    active_version: int | None = None,
    canary_version: int | None = None,
) -> PromptVersionRegistry:
    """Build a validated prompt version registry."""
    latest_version = max((record.version for record in versions), default=None)
    return PromptVersionRegistry(
        manifest_id=manifest_id,
        storage=storage,
        versions=versions,
        active_version=active_version,
        canary_version=canary_version,
        latest_version=latest_version,
    )
