"""User override policy and validation boundaries for prompt customization."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


OverrideSection = Literal[
    "style_instructions",
    "business_glossary",
    "few_shot_examples",
    "response_format_hint",
    "domain_filters",
]


ImmutableSection = Literal[
    "safety_guardrails",
    "required_placeholders",
    "disallowed_operations",
    "read_only_enforcement",
    "tenant_isolation",
    "approval_workflow",
]


class PromptUserOverridePolicy(BaseModel):
    """Boundaries that control which prompt sections users may override."""

    policy_id: str = Field(default="override-policy-v1", min_length=3, max_length=128)
    customizable_sections: tuple[OverrideSection, ...] = Field(
        default=(
            "style_instructions",
            "business_glossary",
            "few_shot_examples",
            "response_format_hint",
            "domain_filters",
        )
    )
    immutable_sections: tuple[ImmutableSection, ...] = Field(
        default=(
            "safety_guardrails",
            "required_placeholders",
            "disallowed_operations",
            "read_only_enforcement",
            "tenant_isolation",
            "approval_workflow",
        )
    )
    max_override_payload_chars: int = Field(default=4000, ge=200, le=20000)
    require_non_empty_rationale: bool = Field(default=True)

    @model_validator(mode="after")
    def validate_policy(self) -> "PromptUserOverridePolicy":
        if len(set(self.customizable_sections)) != len(self.customizable_sections):
            raise ValueError("customizable_sections contains duplicates")
        if len(set(self.immutable_sections)) != len(self.immutable_sections):
            raise ValueError("immutable_sections contains duplicates")
        return self


class PromptUserOverrideRequest(BaseModel):
    """Single user customization request for a prompt section."""

    manifest_id: str = Field(min_length=3, max_length=128)
    requested_by: str = Field(min_length=1, max_length=128)
    section: str = Field(min_length=3, max_length=128)
    value: str = Field(min_length=1)
    rationale: str = Field(min_length=5, max_length=2000)


def validate_user_override_request(
    request: PromptUserOverrideRequest, policy: PromptUserOverridePolicy
) -> None:
    """Validate user override request against policy boundaries.

    Raises:
        ValueError: If override request violates policy constraints.
    """
    section = request.section.strip().lower()

    if section in policy.immutable_sections:
        raise ValueError(f"Section '{section}' is immutable and cannot be overridden")

    if section not in policy.customizable_sections:
        allowed = ", ".join(policy.customizable_sections)
        raise ValueError(
            f"Section '{section}' is not customizable. Allowed sections: {allowed}"
        )

    payload_size = len(request.value)
    if payload_size > policy.max_override_payload_chars:
        raise ValueError(
            "Override value exceeds max_override_payload_chars "
            f"({payload_size} > {policy.max_override_payload_chars})"
        )

    if policy.require_non_empty_rationale and not request.rationale.strip():
        raise ValueError("Override request must include a non-empty rationale")


def get_default_user_override_policy() -> PromptUserOverridePolicy:
    """Return the default user override policy used by the project."""
    return PromptUserOverridePolicy()
