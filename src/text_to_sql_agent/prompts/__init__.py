"""Prompt templates and prompt-scope contracts."""

__version__ = "0.0.1"

from .dialect_scope import (
    DIALECT_SCOPE_MATRIX,
    DialectPromptScope,
    get_dialect_prompt_scope,
    list_supported_dialects,
)
from .change_request import (
    PromptChangeApproval,
    PromptChangeRequest,
    build_prompt_change_request,
)
from .evaluation_gates import (
    PromptEvaluationGateProfile,
    PromptEvaluationScorecard,
    PromptGateDecision,
    PromptMetricScore,
    PromptMetricThreshold,
    evaluate_prompt_scorecard,
    get_default_evaluation_gate_profile,
)
from .prompt_manifest import (
    PromptApprovalMetadata,
    PromptAuditMetadata,
    PromptManifestEnterprise,
    PromptManifestMVP,
    PromptRollout,
    TenantIsolationPolicy,
    build_enterprise_manifest,
    build_mvp_manifest,
)
from .storage_registry import (
    PromptOwnership,
    PromptStorageConfig,
    PromptVersionRecord,
    PromptVersionRegistry,
    build_prompt_version_registry,
)
from .override_policy import (
    PromptUserOverridePolicy,
    PromptUserOverrideRequest,
    get_default_user_override_policy,
    validate_user_override_request,
)

__all__ = [
    "DIALECT_SCOPE_MATRIX",
    "DialectPromptScope",
    "get_dialect_prompt_scope",
    "list_supported_dialects",
    "PromptChangeApproval",
    "PromptChangeRequest",
    "PromptEvaluationGateProfile",
    "PromptEvaluationScorecard",
    "PromptGateDecision",
    "PromptMetricScore",
    "PromptMetricThreshold",
    "PromptApprovalMetadata",
    "PromptAuditMetadata",
    "PromptManifestEnterprise",
    "PromptManifestMVP",
    "PromptOwnership",
    "PromptRollout",
    "PromptStorageConfig",
    "TenantIsolationPolicy",
    "PromptVersionRecord",
    "PromptVersionRegistry",
    "build_prompt_change_request",
    "evaluate_prompt_scorecard",
    "build_enterprise_manifest",
    "build_mvp_manifest",
    "build_prompt_version_registry",
    "PromptUserOverridePolicy",
    "PromptUserOverrideRequest",
    "get_default_user_override_policy",
    "validate_user_override_request",
    "get_default_evaluation_gate_profile",
]
