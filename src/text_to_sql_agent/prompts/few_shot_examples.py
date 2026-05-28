"""Domain few-shot examples for natural-language to SQL generation."""

from __future__ import annotations

from dataclasses import dataclass

from .dialect_scope import DialectName


@dataclass(frozen=True, slots=True)
class FewShotExample:
    """One question-to-SQL training example for prompt injection."""

    input: str
    query: str
    tables: tuple[str, ...] = ()


_SQLITE_ACTIVITY_TABLE = ("activities_eventdate",)


def _sqlite_activity_example(*, input: str, query: str) -> FewShotExample:
    return FewShotExample(input=input, query=query, tables=_SQLITE_ACTIVITY_TABLE)


SQLITE_FEW_SHOT_EXAMPLES: tuple[FewShotExample, ...] = (
    _sqlite_activity_example(
        input="Get activities for country UA.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE (countrycode = 'UA' OR countrycodegeo = 'UA');"
        ),
    ),
    _sqlite_activity_example(
        input="Get userid from activities for country US.",
        query=(
            "SELECT userid FROM activities_eventdate "
            "WHERE (countrycode = 'US' OR countrycodegeo = 'US');"
        ),
    ),
    _sqlite_activity_example(
        input="Get activities for countries UA, US",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE (countrycode IN ('UA', 'US') OR countrycodegeo IN ('UA', 'US'));"
        ),
    ),
    _sqlite_activity_example(
        input="Get activities for verticals 1,2,3,4,5",
        query="SELECT * FROM activities_eventdate WHERE verticalid IN (1,2,3,4,5);",
    ),
    _sqlite_activity_example(
        input="Get activities for isps 2, 3",
        query="SELECT * FROM activities_eventdate WHERE ispid IN (2,3);",
    ),
    _sqlite_activity_example(
        input="Get activities for entered from 1609477200 to 1640581200",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE dtentered >= 1609477200 AND dtentered <= 1640581200;"
        ),
    ),
    _sqlite_activity_example(
        input="Get activities for entered from 1992-09-25 to 2024-09-25",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE dtentered >= strftime('%s', '1992-09-25') "
            "AND dtentered <= strftime('%s', '2024-09-25');"
        ),
    ),
    _sqlite_activity_example(
        input="Get activities by id.",
        query="SELECT * FROM activities_eventdate WHERE id = 123;",
    ),
    _sqlite_activity_example(
        input="Get activities by activity_id.",
        query="SELECT * FROM activities_eventdate WHERE activity_id = 456;",
    ),
    _sqlite_activity_example(
        input="Get activities by exact event date.",
        query="SELECT * FROM activities_eventdate WHERE eventdate = '2024-12-01';",
    ),
    _sqlite_activity_example(
        input="Get activities by event date range.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE eventdate BETWEEN '2024-01-01' AND '2024-12-31';"
        ),
    ),
    _sqlite_activity_example(
        input="Get userid from activities for state CA.",
        query=(
            "SELECT userid FROM activities_eventdate "
            "WHERE (statecode = 'CA' OR statecodegeo = 'CA') LIMIT 10;"
        ),
    ),
    _sqlite_activity_example(
        input="Get userid from activities for city New York.",
        query=(
            "SELECT userid FROM activities_eventdate "
            "WHERE (city = 'New York' OR citygeo = 'New York') LIMIT 10;"
        ),
    ),
    _sqlite_activity_example(
        input="Get activities by region.",
        query="SELECT * FROM activities_eventdate WHERE region = 'Kyivska';",
    ),
    _sqlite_activity_example(
        input="Get activities by city.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE (city = 'Kyiv' OR citygeo = 'Kyiv');"
        ),
    ),
    _sqlite_activity_example(
        input="Get activities by latitude/longitude bounding box.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE latitude BETWEEN 49.0 AND 50.0 "
            "AND longitude BETWEEN 30.0 AND 31.0;"
        ),
    ),
    _sqlite_activity_example(
        input="Get activities by activity type.",
        query="SELECT * FROM activities_eventdate WHERE activitytype = 'webinar';",
    ),
    _sqlite_activity_example(
        input="Get activities by activity name contains 'conference'.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE LOWER(activityname) LIKE '%conference%';"
        ),
    ),
    _sqlite_activity_example(
        input="Get activities by source.",
        query="SELECT * FROM activities_eventdate WHERE source = 'external';",
    ),
    _sqlite_activity_example(
        input="Get activities created in a date range.",
        query=(
            "SELECT * FROM activities_eventdate "
            "WHERE created_at BETWEEN '2024-01-01' AND '2024-06-30';"
        ),
    ),
    _sqlite_activity_example(
        input="Get activities updated after a date.",
        query="SELECT * FROM activities_eventdate WHERE updated_at >= '2024-12-01';",
    ),
)

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
