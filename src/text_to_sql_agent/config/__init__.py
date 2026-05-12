"""
Configuration module for text-to-sql-agent.

Provides centralized configuration management using Pydantic and environment variables.
"""

__version__ = "0.0.1"

from text_to_sql_agent.config.logging import LoggingConfig, get_logger, setup_logging

__all__ = [
    "LoggingConfig",
    "setup_logging",
    "get_logger",
]
