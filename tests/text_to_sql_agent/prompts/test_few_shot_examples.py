"""Tests for domain few-shot example registry."""

import pytest

from text_to_sql_agent.prompts.few_shot_examples import (
    SQLITE_FEW_SHOT_EXAMPLES,
    format_few_shot_examples,
    get_few_shot_examples,
    get_few_shot_examples_for_tables,
    get_formatted_few_shot_examples,
)


def test_sqlite_includes_activities_country_example() -> None:
    assert len(SQLITE_FEW_SHOT_EXAMPLES) >= 1
    example = SQLITE_FEW_SHOT_EXAMPLES[0]
    assert example.input == "Get activities for country UA."
    assert "activities_eventdate" in example.query
    assert "countrycode = 'UA'" in example.query
    assert "countrycodegeo = 'UA'" in example.query


def test_sqlite_examples_are_read_only_select() -> None:
    forbidden = ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE ")
    for example in SQLITE_FEW_SHOT_EXAMPLES:
        normalized = example.query.upper()
        assert normalized.startswith("SELECT ")
        assert all(token not in normalized for token in forbidden)


def test_get_few_shot_examples_is_case_insensitive() -> None:
    examples = get_few_shot_examples("SQLite")
    assert examples == SQLITE_FEW_SHOT_EXAMPLES


def test_get_few_shot_examples_rejects_unsupported_dialect() -> None:
    with pytest.raises(ValueError, match="Unsupported dialect"):
        get_few_shot_examples("sqlserver")


def test_format_few_shot_examples_includes_question_and_sql() -> None:
    rendered = format_few_shot_examples(SQLITE_FEW_SHOT_EXAMPLES)
    assert "Question: Get activities for country UA." in rendered
    assert "SQL: SELECT * FROM activities_eventdate" in rendered


def test_get_formatted_few_shot_examples_for_empty_dialect() -> None:
    assert get_formatted_few_shot_examples("postgresql") == ""


def test_get_few_shot_examples_for_tables_filters_by_table_name() -> None:
    filtered = get_few_shot_examples_for_tables("sqlite", ["activities_eventdate"])
    assert len(filtered) == len(SQLITE_FEW_SHOT_EXAMPLES)
    assert all("activities_eventdate" in example.tables for example in filtered)


def test_get_few_shot_examples_for_tables_returns_empty_for_non_matching_table() -> None:
    filtered = get_few_shot_examples_for_tables("sqlite", ["users"])
    assert filtered == ()


def test_get_formatted_few_shot_examples_for_selected_tables_without_matches() -> None:
    assert get_formatted_few_shot_examples("sqlite", selected_tables=["users"]) == ""
