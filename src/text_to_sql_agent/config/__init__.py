"""
Configuration module for text-to-sql-agent.

Provides centralized configuration management using Pydantic and environment variables.
"""

__version__ = "0.0.1"

from text_to_sql_agent.config.logging import LoggingConfig, get_logger, setup_logging
from text_to_sql_agent.config.secrets import (
    AwsSecretsManagerProvider,
    FileSecretsProvider,
    PLACEHOLDER_VALUE,
    SecretResolutionError,
    SecretResolutionResult,
    resolve_secret_placeholders,
)
from text_to_sql_agent.config.settings import (
    ConversationAuthSettings,
    load_conversation_auth_settings,
    load_runtime_environment,
)

__all__ = [
    "AwsSecretsManagerProvider",
    "FileSecretsProvider",
    "LoggingConfig",
    "PLACEHOLDER_VALUE",
    "SecretResolutionError",
    "SecretResolutionResult",
    "ConversationAuthSettings",
    "load_conversation_auth_settings",
    "load_runtime_environment",
    "setup_logging",
    "get_logger",
    "resolve_secret_placeholders",
]
