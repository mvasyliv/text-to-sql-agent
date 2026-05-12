"""Tests for prompt metrics and evaluation gates."""

import pytest

from text_to_sql_agent.prompts.evaluation_gates import (
    PromptEvaluationGateProfile,
    PromptEvaluationScorecard,
    PromptMetricScore,
    PromptMetricThreshold,
    evaluate_prompt_scorecard,
    get_default_evaluation_gate_profile,
)


def test_default_profile_passes_with_valid_metrics() -> None:
    gate = get_default_evaluation_gate_profile()
    scorecard = PromptEvaluationScorecard(
        manifest_id="mvp.sales.monthly",
        version=3,
        sample_size=120,
        scores=(
            PromptMetricScore(metric_name="validity_rate", value=0.99),
            PromptMetricScore(metric_name="execution_success_rate", value=0.97),
            PromptMetricScore(metric_name="policy_violation_rate", value=0.002),
            PromptMetricScore(metric_name="leakage_rate", value=0.001),
        ),
    )

    decision = evaluate_prompt_scorecard(scorecard, gate)
    assert decision.passed is True
    assert decision.blocking_violations == ()


def test_hard_fail_metric_blocks_promotion() -> None:
    gate = get_default_evaluation_gate_profile()
    scorecard = PromptEvaluationScorecard(
        manifest_id="mvp.sales.monthly",
        version=4,
        sample_size=140,
        scores=(
            PromptMetricScore(metric_name="validity_rate", value=0.96),
            PromptMetricScore(metric_name="execution_success_rate", value=0.97),
            PromptMetricScore(metric_name="policy_violation_rate", value=0.002),
            PromptMetricScore(metric_name="leakage_rate", value=0.001),
        ),
    )

    decision = evaluate_prompt_scorecard(scorecard, gate)
    assert decision.passed is False
    assert any("validity_rate below minimum" in item for item in decision.blocking_violations)


def test_missing_required_metric_blocks_promotion() -> None:
    gate = get_default_evaluation_gate_profile()
    scorecard = PromptEvaluationScorecard(
        manifest_id="mvp.sales.monthly",
        version=5,
        sample_size=100,
        scores=(
            PromptMetricScore(metric_name="validity_rate", value=0.99),
            PromptMetricScore(metric_name="execution_success_rate", value=0.97),
            PromptMetricScore(metric_name="policy_violation_rate", value=0.002),
        ),
    )

    decision = evaluate_prompt_scorecard(scorecard, gate)
    assert decision.passed is False
    assert any("missing required metric 'leakage_rate'" in item for item in decision.blocking_violations)


def test_low_sample_size_creates_warning_not_blocking_failure() -> None:
    gate = get_default_evaluation_gate_profile()
    scorecard = PromptEvaluationScorecard(
        manifest_id="mvp.sales.monthly",
        version=6,
        sample_size=10,
        scores=(
            PromptMetricScore(metric_name="validity_rate", value=0.99),
            PromptMetricScore(metric_name="execution_success_rate", value=0.99),
            PromptMetricScore(metric_name="policy_violation_rate", value=0.0),
            PromptMetricScore(metric_name="leakage_rate", value=0.0),
        ),
    )

    decision = evaluate_prompt_scorecard(scorecard, gate)
    assert decision.passed is True
    assert any("sample_size below minimum" in item for item in decision.warnings)


def test_gate_profile_requires_unique_metric_thresholds() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        PromptEvaluationGateProfile(
            profile_id="bad-gate",
            minimum_samples=50,
            thresholds=(
                PromptMetricThreshold(
                    metric_name="validity_rate",
                    direction="higher_better",
                    min_value=0.9,
                    hard_fail=True,
                ),
                PromptMetricThreshold(
                    metric_name="validity_rate",
                    direction="higher_better",
                    min_value=0.95,
                    hard_fail=True,
                ),
            ),
        )
