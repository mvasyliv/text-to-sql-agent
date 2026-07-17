"""Domain few-shot examples for natural-language to SQL generation."""

from __future__ import annotations

from .dialect_scope import DialectName
from .few_shot_models import FewShotExample
from .few_shot_examples_activities_eventdate import SQLITE_ACTIVITIES_EVENTDATE_EXAMPLES
from .few_shot_examples_optins import SQLITE_OPTINS_EXAMPLES



SQLITE_FEW_SHOT_EXAMPLES: tuple[FewShotExample, ...] = SQLITE_ACTIVITIES_EVENTDATE_EXAMPLES + SQLITE_OPTINS_EXAMPLES    

_FEW_SHOT_BY_DIALECT: dict[DialectName, tuple[FewShotExample, ...]] = {
    "sqlite": SQLITE_FEW_SHOT_EXAMPLES,
    "postgresql": (),
    "mysql": (),
    "athena": (),
}


def get_few_shot_examples(dialect: str) -> tuple[FewShotExample, ...]:
    """Return domain few-shot examples for a supported SQL dialect."""
    normalized = dialect.strip().lower()
    if normalized not in _FEW_SHOT_BY_DIALECT:
        supported = ", ".join(sorted(_FEW_SHOT_BY_DIALECT))
        raise ValueError(f"Unsupported dialect '{dialect}'. Supported: {supported}")
    return _FEW_SHOT_BY_DIALECT[normalized]  # type: ignore[index]


def _normalize_table_names(table_names: list[str] | tuple[str, ...] | None) -> set[str]:
    if not table_names:
        return set()
    return {name.strip().lower() for name in table_names if name and name.strip()}


def get_few_shot_examples_for_tables(
    dialect: str,
    selected_tables: list[str] | tuple[str, ...] | None,
) -> tuple[FewShotExample, ...]:
    """Return few-shot examples filtered by selected table names.

    When selected_tables is empty or None, all examples for the dialect are returned.
    """
    examples = get_few_shot_examples(dialect)
    normalized_selected = _normalize_table_names(selected_tables)
    if not normalized_selected:
        return examples

    filtered = tuple(
        ex
        for ex in examples
        if _normalize_table_names(ex.tables) & normalized_selected
    )
    return filtered


def format_few_shot_examples(examples: tuple[FewShotExample, ...]) -> str:
    """Render few-shot examples as prompt text for the few_shot_examples section."""
    if not examples:
        return ""

    blocks: list[str] = []
    for index, example in enumerate(examples, start=1):
        blocks.append(
            "\n".join(
                (
                    f"Example {index}:",
                    f"Question: {example.input}",
                    f"SQL: {example.query}",
                )
            )
        )
    return "\n\n".join(blocks)


def get_formatted_few_shot_examples(
    dialect: str,
    selected_tables: list[str] | tuple[str, ...] | None = None,
) -> str:
    """Return formatted few-shot block filtered by dialect and selected tables."""
    examples = get_few_shot_examples_for_tables(dialect, selected_tables)
    return format_few_shot_examples(examples)
