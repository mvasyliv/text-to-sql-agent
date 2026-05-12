"""Tests for MVP prompt manifest contract."""

import pytest

from text_to_sql_agent.prompts.prompt_manifest import (
    PromptManifestMVP,
    PromptRollout,
    build_mvp_manifest,
)


VALID_TEMPLATE = (
    "You are a SQL generator.\n"
    "Question: {user_request}\n"
    "Schema: {schema_context}\n"
    "Return one read-only SQL query."
)


def test_build_mvp_manifest_with_defaults() -> None:
    manifest = build_mvp_manifest(
        manifest_id="mvp.sales.monthly",
        version=1,
        dialect="postgresql",
        owner="analytics-team",
        prompt_template=VALID_TEMPLATE,
    )

    assert manifest.status == "draft"
    assert manifest.read_only_required is True
    assert manifest.rollout.strategy == "off"
    assert manifest.rollout.percentage == 0
    assert "select_or_with_only" in manifest.required_guardrails


def test_active_manifest_requires_non_off_rollout() -> None:
    with pytest.raises(ValueError, match="Active manifest must have rollout strategy"):
        PromptManifestMVP(
            manifest_id="mvp.sales.monthly",
            version=2,
            dialect="mysql",
            status="active",
            owner="analytics-team",
            prompt_template=VALID_TEMPLATE,
            rollout=PromptRollout(strategy="off", percentage=0),
        )


def test_template_requires_required_placeholders() -> None:
    with pytest.raises(ValueError, match="missing required placeholders"):
        build_mvp_manifest(
            manifest_id="mvp.sales.invalid",
            version=1,
            dialect="athena",
            owner="analytics-team",
            prompt_template="Question: {user_request}",
        )


def test_mvp_contract_enforces_read_only_mode() -> None:
    with pytest.raises(ValueError, match="read_only_required=True"):
        PromptManifestMVP(
            manifest_id="mvp.sales.override",
            version=1,
            dialect="sqlite",
            owner="analytics-team",
            prompt_template=VALID_TEMPLATE,
            read_only_required=False,
        )


@pytest.mark.parametrize(
    ("strategy", "percentage"),
    [("off", 10), ("full", 99), ("canary", 0), ("canary", 100)],
)
def test_rollout_strategy_percentage_consistency(
    strategy: str, percentage: int
) -> None:
    with pytest.raises(ValueError):
        PromptRollout(strategy=strategy, percentage=percentage)


def test_disallowed_operations_are_normalized_and_unique() -> None:
    manifest = PromptManifestMVP(
        manifest_id="mvp.sales.ops",
        version=1,
        dialect="postgresql",
        owner="analytics-team",
        prompt_template=VALID_TEMPLATE,
        disallowed_operations=("drop", " delete "),
    )

    assert manifest.disallowed_operations == ("DROP", "DELETE")

    with pytest.raises(ValueError, match="contains duplicates"):
        PromptManifestMVP(
            manifest_id="mvp.sales.ops2",
            version=1,
            dialect="postgresql",
            owner="analytics-team",
            prompt_template=VALID_TEMPLATE,
            disallowed_operations=("drop", "DROP"),
        )
