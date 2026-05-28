"""Tests for SQL generation prompt builder."""

from text_to_sql_agent.prompts.sql_generation_prompt import build_sql_generation_prompt


def test_build_sql_generation_prompt_includes_few_shot_for_matching_table() -> None:
    prompt = build_sql_generation_prompt(
        user_request="Get activities for country UA",
        schema_context="TABLE activities_eventdate\n  id integer",
        dialect="sqlite",
        selected_tables=["activities_eventdate"],
    )

    assert "Few-Shot Examples:" in prompt
    assert "Question: Get activities for country UA." in prompt


def test_build_sql_generation_prompt_uses_none_when_no_matching_few_shot() -> None:
    prompt = build_sql_generation_prompt(
        user_request="Show all users",
        schema_context="TABLE users\n  id integer",
        dialect="sqlite",
        selected_tables=["users"],
    )

    assert "Few-Shot Examples:" in prompt
    assert "(none)" in prompt
