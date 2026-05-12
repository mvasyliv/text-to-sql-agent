"""Prompt metrics and evaluation gates for version promotion decisions."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


MetricDirection = Literal["higher_better", "lower_better"]


class PromptMetricThreshold(BaseModel):
    """Threshold definition for one prompt evaluation metric."""

    metric_name: str = Field(min_length=1, max_length=128)
    direction: MetricDirection
    min_value: float | None = Field(default=None, ge=0.0, le=1.0)
    max_value: float | None = Field(default=None, ge=0.0, le=1.0)
    hard_fail: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_bounds(self) -> "PromptMetricThreshold":
        if self.min_value is None and self.max_value is None:
            raise ValueError("at least one of min_value or max_value must be provided")
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValueError("min_value cannot be greater than max_value")
        return self


class PromptEvaluationGateProfile(BaseModel):
    """Gate profile used to evaluate prompt quality and safety metrics."""

    profile_id: str = Field(min_length=3, max_length=128)
    minimum_samples: int = Field(default=50, ge=1, le=1_000_000)
    thresholds: tuple[PromptMetricThreshold, ...]

    @model_validator(mode="after")
    def validate_unique_metrics(self) -> "PromptEvaluationGateProfile":
        names = [threshold.metric_name for threshold in self.thresholds]
        if len(set(names)) != len(names):
            raise ValueError("threshold metric names must be unique")
        return self


class PromptMetricScore(BaseModel):
    """Observed metric value for a prompt version evaluation run."""

    metric_name: str = Field(min_length=1, max_length=128)
    value: float = Field(ge=0.0, le=1.0)


class PromptEvaluationScorecard(BaseModel):
    """Aggregated metrics for one prompt version evaluation run."""

    manifest_id: str = Field(min_length=3, max_length=128)
    version: int = Field(ge=1)
    sample_size: int = Field(ge=1)
    scores: tuple[PromptMetricScore, ...]

    @model_validator(mode="after")
    def validate_unique_scores(self) -> "PromptEvaluationScorecard":
        names = [score.metric_name for score in self.scores]
        if len(set(names)) != len(names):
            raise ValueError("score metric names must be unique")
        return self


class PromptGateDecision(BaseModel):
    """Gate result for a prompt evaluation scorecard."""

    passed: bool
    blocking_violations: tuple[str, ...] = Field(default=())
    warnings: tuple[str, ...] = Field(default=())


def get_default_evaluation_gate_profile() -> PromptEvaluationGateProfile:
    """Return default gate profile for prompt promotion decisions."""
    return PromptEvaluationGateProfile(
        profile_id="default-v1",
        minimum_samples=50,
        thresholds=(
            PromptMetricThreshold(
                metric_name="validity_rate",
                direction="higher_better",
                min_value=0.98,
                hard_fail=True,
            ),
            PromptMetricThreshold(
                metric_name="execution_success_rate",
                direction="higher_better",
                min_value=0.95,
                hard_fail=True,
            ),
            PromptMetricThreshold(
                metric_name="policy_violation_rate",
                direction="lower_better",
                max_value=0.01,
                hard_fail=True,
            ),
            PromptMetricThreshold(
                metric_name="leakage_rate",
                direction="lower_better",
                max_value=0.005,
                hard_fail=True,
            ),
        ),
    )


def evaluate_prompt_scorecard(
    scorecard: PromptEvaluationScorecard,
    gate_profile: PromptEvaluationGateProfile,
) -> PromptGateDecision:
    """Evaluate scorecard against gate profile.

    Returns blocking violations for hard gate failures and warnings for
    non-blocking issues.
    """
    violations: list[str] = []
    warnings: list[str] = []

    if scorecard.sample_size < gate_profile.minimum_samples:
        warnings.append(
            "sample_size below minimum threshold "
            f"({scorecard.sample_size} < {gate_profile.minimum_samples})"
        )

    observed = {score.metric_name: score.value for score in scorecard.scores}

    for threshold in gate_profile.thresholds:
        if threshold.metric_name not in observed:
            violations.append(
                f"missing required metric '{threshold.metric_name}'"
            )
            continue

        value = observed[threshold.metric_name]
        metric_violations: list[str] = []

        if threshold.min_value is not None and value < threshold.min_value:
            metric_violations.append(
                f"{threshold.metric_name} below minimum ({value:.4f} < {threshold.min_value:.4f})"
            )
        if threshold.max_value is not None and value > threshold.max_value:
            metric_violations.append(
                f"{threshold.metric_name} above maximum ({value:.4f} > {threshold.max_value:.4f})"
            )

        if metric_violations:
            if threshold.hard_fail:
                violations.extend(metric_violations)
            else:
                warnings.extend(metric_violations)

    return PromptGateDecision(
        passed=not violations,
        blocking_violations=tuple(violations),
        warnings=tuple(warnings),
    )
