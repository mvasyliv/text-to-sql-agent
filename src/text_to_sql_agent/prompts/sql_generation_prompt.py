"""Prompt builder for SQL generation with table-aware few-shot examples."""

from __future__ import annotations

from .few_shot_examples import get_formatted_few_shot_examples


def build_sql_generation_prompt(
    *,
    user_request: str,
    schema_context: str,
    dialect: str,
    selected_tables: list[str] | tuple[str, ...] | None = None,
) -> str:
    """Build SQL generation prompt text for observability and LLM integrations."""
    few_shot_block = get_formatted_few_shot_examples(
        dialect,
        selected_tables=selected_tables,
    )

    sections = [
        "You are a read-only SQL generator.",
        f"Dialect: {dialect}",
        "",
        "Schema Context:",
        schema_context.strip() or "(empty)",
        "",
        "Few-Shot Examples:",
        few_shot_block if few_shot_block else "(none)",
        "",
        "User Request:",
        user_request.strip(),
        "",
        "Generate one read-only SQL query.",
    ]
    return "\n".join(sections)
