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

__all__ = [
    "AwsSecretsManagerProvider",
    "FileSecretsProvider",
    "LoggingConfig",
    "PLACEHOLDER_VALUE",
    "SecretResolutionError",
    "SecretResolutionResult",
    "setup_logging",
    "get_logger",
    "resolve_secret_placeholders",
]
