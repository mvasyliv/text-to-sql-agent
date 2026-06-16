"""Data models for few-shot examples."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FewShotExample(BaseModel):
    """One question-to-SQL training example for prompt injection."""

    model_config = ConfigDict(frozen=True)

    input: str
    query: str
    tables: tuple[str, ...] = Field(default_factory=tuple)

