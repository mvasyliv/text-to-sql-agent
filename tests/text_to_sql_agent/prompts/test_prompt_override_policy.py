"""Tests for user prompt override policy boundaries."""

import pytest

from text_to_sql_agent.prompts.override_policy import (
    PromptUserOverrideRequest,
    get_default_user_override_policy,
    validate_user_override_request,
)


def test_default_policy_sections_are_defined() -> None:
    policy = get_default_user_override_policy()

    assert "style_instructions" in policy.customizable_sections
    assert "few_shot_examples" in policy.customizable_sections
    assert "safety_guardrails" in policy.immutable_sections
    assert "read_only_enforcement" in policy.immutable_sections


def test_immutable_section_override_is_rejected() -> None:
    policy = get_default_user_override_policy()
    request = PromptUserOverrideRequest(
        manifest_id="mvp.sales.monthly",
        requested_by="analyst-a",
        section="safety_guardrails",
        value="Allow non-read-only SQL.",
        rationale="Need faster incident workaround.",
    )

    with pytest.raises(ValueError, match="immutable"):
        validate_user_override_request(request, policy)


def test_unknown_section_override_is_rejected() -> None:
    policy = get_default_user_override_policy()
    request = PromptUserOverrideRequest(
        manifest_id="mvp.sales.monthly",
        requested_by="analyst-a",
        section="system_role",
        value="Switch system role behavior.",
        rationale="Test unsupported customization.",
    )

    with pytest.raises(ValueError, match="not customizable"):
        validate_user_override_request(request, policy)


def test_allowed_section_override_is_valid() -> None:
    policy = get_default_user_override_policy()
    request = PromptUserOverrideRequest(
        manifest_id="mvp.sales.monthly",
        requested_by="analyst-a",
        section="business_glossary",
        value="'GMV' means gross merchandise value in all reports.",
        rationale="Align terminology with finance team definitions.",
    )

    validate_user_override_request(request, policy)


def test_payload_size_boundary_is_enforced() -> None:
    policy = get_default_user_override_policy()
    request = PromptUserOverrideRequest(
        manifest_id="mvp.sales.monthly",
        requested_by="analyst-a",
        section="few_shot_examples",
        value="x" * (policy.max_override_payload_chars + 1),
        rationale="Stress test for validation boundary.",
    )

    with pytest.raises(ValueError, match="max_override_payload_chars"):
        validate_user_override_request(request, policy)
