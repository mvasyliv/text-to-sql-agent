"""
Logging configuration module using loguru.

Provides structured logging setup based on environment settings from .env files.
Supports JSON output for production and readable text format for development.
"""

import sys
from typing import Literal

from loguru import logger
from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Logging configuration model."""

    level: str = Field(
        default="INFO",
        description="Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    format: Literal["text", "json"] = Field(
        default="text",
        description="Log format: text for human-readable, json for production",
    )
    output: Literal["stdout", "file", "both"] = Field(
        default="stdout",
        description="Where to output logs: stdout, file, or both",
    )
    file_path: str | None = Field(
        default=None,
        description="File path for log output (required if output='file' or 'both')",
    )
    retention_days: int = Field(
        default=30,
        description="Number of days to retain log files (if using file output)",
    )
    rotation_size: str = Field(
        default="100MB",
        description="Log file rotation size (e.g., '100MB', '1GB')",
    )

    # Per-module log levels
    level_agent: str = Field(default="DEBUG", description="Log level for agent module")
    level_service: str = Field(
        default="DEBUG", description="Log level for service module"
    )
    level_repository: str = Field(
        default="DEBUG", description="Log level for repository module"
    )
    level_graph: str = Field(default="INFO", description="Log level for graph module")
    level_model: str = Field(default="INFO", description="Log level for model module")
    level_prompt: str = Field(default="INFO", description="Log level for prompt module")

    class Config:
        """Pydantic configuration."""

        str_strip_whitespace = True


def setup_logging(config: LoggingConfig) -> None:
    """
    Configure loguru logger based on LoggingConfig.

    Removes default handler and adds configured handlers for stdout and/or file.
    Supports per-module log level overrides.

    Args:
        config: LoggingConfig instance with logging settings.

    Raises:
        ValueError: If file output is requested but file_path is not provided.
    """
    # Remove default handler
    logger.remove()

    # Validate file output configuration
    if config.output in ("file", "both") and not config.file_path:
        raise ValueError(
            "file_path must be provided when output is 'file' or 'both'"
        )

    # Determine format string based on environment
    if config.format == "json":
        # Minimal JSON format for production
        log_format = (
            '{{time:YYYY-MM-DD HH:mm:ss}} | {{level: <8}} | {{name}}:{{function}}:{{line}} | {{message}}'
        )
    else:
        # Readable text format for development
        log_format = (
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Add stdout handler
    if config.output in ("stdout", "both"):
        logger.add(
            sys.stdout,
            format=log_format,
            level=config.level,
            colorize=(config.format == "text"),
        )

    # Add file handler
    if config.output in ("file", "both"):
        logger.add(
            config.file_path,
            format=log_format,
            level=config.level,
            rotation=config.rotation_size,
            retention=f"{config.retention_days} days",
            compression="gzip",
        )

    # Configure per-module log levels
    module_levels = {
        "text_to_sql_agent.agents": config.level_agent,
        "text_to_sql_agent.services": config.level_service,
        "text_to_sql_agent.repositories": config.level_repository,
        "text_to_sql_agent.graphs": config.level_graph,
        "text_to_sql_agent.models": config.level_model,
        "text_to_sql_agent.prompts": config.level_prompt,
    }

    for module_name, level in module_levels.items():
        logger.enable(module_name)
        # Note: loguru doesn't have built-in per-module level filtering in v0.7
        # For detailed per-module filtering, consider using a filter function or middleware


def get_logger(name: str) -> "logger":
    """
    Get a configured logger instance for a module.

    Args:
        name: Module name (typically __name__).

    Returns:
        Configured loguru logger bound to the module name.
    """
    return logger.bind(name=name)
