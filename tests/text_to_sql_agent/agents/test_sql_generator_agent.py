"""Tests for SQL generator agent (T-2026-05-18-043)."""
import text_to_sql_agent.agents.sql_generator_agent as sql_generator_agent_module
from text_to_sql_agent.agents.sql_generator_agent import (
    build_sql_generator_node,
    generate_read_only_sql,
)
def _schema_context() -> str:
    return (
        "-- Database: testdb (sqlite)\n\n"
        "TABLE users\n"
        "  id integer [PK]\n"
        "  name text\n\n"
        "TABLE orders\n"
        "  id integer [PK]\n"
        "  user_id integer [FK]"
    )
def _activities_schema_context() -> str:
    return (
        "-- Database: testdb (sqlite)\n\n"
        "TABLE activities_eventdate\n"
        "  id integer [PK]\n"
        "  userid integer\n"
        "  countrycode text\n"
        "  countrycodegeo text"
    )
class TestGenerateReadOnlySql:
    def test_count_intent_uses_count_query(self):
        result = generate_read_only_sql(
            "How many users are there?",
            _schema_context(),
            dialect="sqlite",
        )
        assert result.intent == "count"
        assert "COUNT(*)" in result.sql
        assert 'FROM "users"' in result.sql
    def test_list_intent_uses_limit(self):
        result = generate_read_only_sql(
            "Show all orders",
            _schema_context(),
            max_limit=50,
        )
        assert result.intent == "list"
        assert result.sql.startswith('SELECT * FROM "orders"')
        assert result.sql.endswith("LIMIT 50")
    def test_falls_back_to_first_table_when_not_mentioned(self):
        result = generate_read_only_sql(
            "Give me data",
            _schema_context(),
        )
        assert 'FROM "users"' in result.sql
    def test_no_tables_returns_probe_query(self):
        result = generate_read_only_sql(
            "Show anything",
            "-- No tables found in database 'testdb'",
        )
        assert result.intent == "probe"
        assert result.sql == "SELECT 1 AS result LIMIT 1"
    def test_selected_tables_with_no_matching_few_shot_sets_zero_count(self):
        result = generate_read_only_sql(
            "Show all users",
            _schema_context(),
            dialect="sqlite",
            selected_tables=["users"],
        )
        assert result.few_shot_count == 0
        assert "Few-Shot Examples:" in result.prompt
    def test_invalid_limit_raises(self):
        try:
            generate_read_only_sql("Show users", _schema_context(), max_limit=0)
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "max_limit" in str(exc)
    def test_llm_sql_is_used_when_available(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: ("SELECT userid FROM activities_eventdate LIMIT 5", "ok"),
        )
        result = generate_read_only_sql(
            "Get users",
            _schema_context(),
            dialect="sqlite",
        )
        assert result.intent == "llm"
        assert "SELECT DISTINCT userid FROM activities_eventdate LIMIT 5" == result.sql
        assert "Few-Shot Examples:" in result.prompt
        assert result.llm_status == "ok"

    def test_llm_only_mode_uses_llm_when_available(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: ("SELECT userid FROM activities_eventdate LIMIT 5", "ok"),
        )
        result = generate_read_only_sql(
            "Get users",
            _schema_context(),
            dialect="sqlite",
            generation_strategy="llm_only",
        )
        assert result.intent == "llm"
        assert "SELECT DISTINCT userid FROM activities_eventdate LIMIT 5" == result.sql

    def test_llm_only_mode_raises_when_llm_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "missing_api_key"),
        )
        try:
            generate_read_only_sql(
                "Show all users",
                _schema_context(),
                dialect="sqlite",
                generation_strategy="llm_only",
            )
            assert False, "Expected RuntimeError"
        except RuntimeError as exc:
            assert "LLM-only generation failed" in str(exc)
    def test_unsafe_llm_response_falls_back_to_deterministic(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "unsafe_output"),
        )
        result = generate_read_only_sql(
            "Show all users",
            _schema_context(),
            dialect="sqlite",
        )
        assert result.intent == "list"
        assert result.sql.startswith('SELECT * FROM "users"')
    def test_uses_matching_few_shot_when_llm_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "missing_api_key"),
        )
        result = generate_read_only_sql(
            "get list userid from activities for country US",
            _activities_schema_context(),
            dialect="sqlite",
            selected_tables=["activities_eventdate"],
        )
        assert result.intent == "few_shot"
        assert "SELECT DISTINCT userid FROM activities_eventdate" in result.sql
        assert "countrycode = 'US'" in result.sql
        assert "countrycodegeo = 'US'" in result.sql
        assert result.llm_user_notice is not None
    def test_exact_phrase_prefers_exact_few_shot_example(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        result = generate_read_only_sql(
            "Get activities for countries UA, US",
            _activities_schema_context(),
            dialect="sqlite",
            selected_tables=["activities_eventdate"],
        )
        assert result.intent == "few_shot"
        assert "countrycode IN ('UA', 'US')" in result.sql
    def test_mismatched_country_codes_does_not_use_partial_few_shot(self, monkeypatch):
        """When user requests different countries, don't use few-shot with partial match."""
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        result = generate_read_only_sql(
            "get list userid from activities for countries US, PL, GB",
            _activities_schema_context(),
            dialect="sqlite",
            selected_tables=["activities_eventdate"],
        )
        # Should fall back to deterministic (not few-shot with UA, US countries)
        assert result.intent == "list"
        # Should not contain the hard-coded few-shot country codes
        assert "UA" not in result.sql
        assert "('UA', 'US')" not in result.sql

    def test_country_filter_is_preserved_in_deterministic_fallback(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        result = generate_read_only_sql(
            "get list userid from activities for countries GB, PL",
            _activities_schema_context(),
            dialect="sqlite",
            selected_tables=["activities_eventdate"],
        )
        assert result.intent == "list"
        assert result.sql.startswith('SELECT DISTINCT userid FROM "activities_eventdate"')
        assert "countrycode IN ('GB', 'PL')" in result.sql or 'countrycode IN ("GB", "PL")' in result.sql
        assert "countrycode IN ('GB', 'PL')" in result.sql
        assert "countrycodegeo IN ('GB', 'PL')" in result.sql
        assert result.sql.endswith("LIMIT 100")

    def test_country_filter_without_comma_is_preserved_in_deterministic_fallback(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        result = generate_read_only_sql(
            "get list userid from activities for countries: gb pl",
            _activities_schema_context(),
            dialect="sqlite",
            selected_tables=["activities_eventdate"],
        )
        assert result.intent == "list"
        assert result.sql.startswith('SELECT DISTINCT userid FROM "activities_eventdate"')
        assert "countrycode IN ('GB', 'PL')" in result.sql or 'countrycode IN ("GB", "PL")' in result.sql
        assert "countrycode IN ('GB', 'PL')" in result.sql
        assert "countrycodegeo IN ('GB', 'PL')" in result.sql

    def test_llm_unavailable_notice_only_for_unavailable_status(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "unsafe_output"),
        )
        result = generate_read_only_sql(
            "Show all users",
            _schema_context(),
            dialect="sqlite",
        )
        assert result.llm_user_notice is None

    def test_optins_userid_with_verticals_few_shot(self, monkeypatch):
        """Test that 'get userid from optins for verticals' uses correct few-shot example."""
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        optins_schema = (
            "-- Database: testdb (sqlite)\n\n"
            "TABLE optins\n"
            "  userid integer\n"
            "  verticalid integer\n"
            "  countrycode text\n"
            "  gender text\n"
            "  dtentered integer"
        )
        result = generate_read_only_sql(
            "get list userid from optins for verticals 1,2,3,4,5",
            optins_schema,
            dialect="sqlite",
            selected_tables=["optins"],
        )
        assert result.intent == "few_shot"
        assert "SELECT DISTINCT userid FROM" in result.sql
        assert "verticalid IN (1,2,3,4,5)" in result.sql
        assert "verticalid IN (1,2,3,4,5)" in result.sql
        assert "SELECT *" not in result.sql

    def test_optins_partial_country_name_rewrites_few_shot_projection(self, monkeypatch):
        """When user writes partial field names, map to schema column in few-shot SQL."""
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        optins_schema = (
            "-- Database: testdb (sqlite)\n\n"
            "TABLE optins\n"
            "  userid integer\n"
            "  verticalid integer\n"
            "  countrycode text\n"
            "  gender text\n"
            "  dtentered integer"
        )
        result = generate_read_only_sql(
            "get country frop optins for verticals 1,2,3,4,5",
            optins_schema,
            dialect="sqlite",
            selected_tables=["optins"],
        )
        assert result.intent == "few_shot"
        assert "SELECT DISTINCT countrycode FROM optins" in result.sql
        assert "verticalid IN (1,2,3,4,5)" in result.sql
        assert "verticalid IN (1,2,3,4,5)" in result.sql
        assert "SELECT *" not in result.sql

    def test_extract_projection_matches_partial_country_token(self):
        """Direct projection extraction maps country -> countrycode."""
        projection = sql_generator_agent_module._extract_projection_from_question(
            "get country frop optins for verticals 1,2,3,4,5",
            ["userid", "verticalid", "countrycode", "gender", "dtentered"],
        )
        assert projection == "countrycode"

    def test_extract_projection_matches_geo_alias(self):
        projection = sql_generator_agent_module._extract_projection_from_question(
            "get geo from activities where country UA",
            ["userid", "countrycode", "countrycodegeo"],
        )
        assert projection == "countrycodegeo"

    def test_extract_projection_matches_entered_alias(self):
        projection = sql_generator_agent_module._extract_projection_from_question(
            "get entered from optins for verticals 1,2,3,4,5",
            ["userid", "verticalid", "countrycode", "gender", "dtentered"],
        )
        assert projection == "dtentered"

    def test_optins_entered_alias_rewrites_few_shot_projection(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        optins_schema = (
            "-- Database: testdb (sqlite)\n\n"
            "TABLE optins\n"
            "  userid integer\n"
            "  verticalid integer\n"
            "  countrycode text\n"
            "  gender text\n"
            "  dtentered integer"
        )
        result = generate_read_only_sql(
            "get entered from optins for entered from 1609477200 to 1640581200",
            optins_schema,
            dialect="sqlite",
            selected_tables=["optins"],
        )
        assert result.intent == "few_shot"
        assert "SELECT DISTINCT dtentered FROM optins" in result.sql
        assert "dtentered >= 1609477200" in result.sql
        assert "dtentered <= 1640581200" in result.sql
        assert "dtentered >= 1609477200" in result.sql
        assert "dtentered <= 1640581200" in result.sql
        assert "SELECT *" not in result.sql

    def test_activities_geo_alias_rewrites_few_shot_projection(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        result = generate_read_only_sql(
            "get geo from activities for country UA",
            _activities_schema_context(),
            dialect="sqlite",
            selected_tables=["activities_eventdate"],
        )
        assert result.intent == "few_shot"
        assert "SELECT DISTINCT countrycodegeo FROM activities_eventdate" in result.sql
        assert "countrycode = 'UA'" in result.sql
        assert "countrycodegeo = 'UA'" in result.sql
    def test_optins_single_column_gets_distinct(self, monkeypatch):
        """Single column projections should get DISTINCT to avoid duplicates."""
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        optins_schema = (
            "-- Database: testdb (sqlite)\n\n"
            "TABLE optins\n"
            "  userid integer\n"
            "  verticalid integer\n"
            "  countrycode text\n"
            "  gender text\n"
            "  dtentered integer"
        )
        result = generate_read_only_sql(
            "get country from optins for verticals 1,2,3,4,5",
            optins_schema,
            dialect="sqlite",
            selected_tables=["optins"],
        )
        assert result.intent == "few_shot"
        assert "SELECT DISTINCT countrycode" in result.sql
        assert "verticalid IN (1,2,3,4,5)" in result.sql

    def test_multiple_columns_no_distinct(self):
        """Multiple columns should not get DISTINCT."""
        projection = sql_generator_agent_module._extract_projection_from_question(
            "get country and userid from optins",
            ["userid", "verticalid", "countrycode", "gender"],
        )
        assert projection == "countrycode, userid"

    def test_maybe_add_distinct_skips_select_star(self):
        """SELECT * should not get DISTINCT."""
        sql = "SELECT * FROM optins WHERE verticalid IN (1,2,3,4,5);"
        result = sql_generator_agent_module._maybe_add_distinct_for_single_column(sql)
        assert result == sql
        assert "DISTINCT" not in result

    def test_maybe_add_distinct_skips_aggregations(self):
        """Aggregations should not get DISTINCT."""
        sql = "SELECT COUNT(*) FROM optins WHERE verticalid IN (1,2,3,4,5);"
        result = sql_generator_agent_module._maybe_add_distinct_for_single_column(sql)
        assert result == sql
        assert "DISTINCT" not in result
class TestBuildSqlGeneratorNode:
    def test_node_populates_generated_sql_and_rationale(self):
        node = build_sql_generator_node(max_limit=25)
        state = {
            "user_question": "Show all users",
            "schema_context": _schema_context(),
            "dialect": "sqlite",
            "selected_tables": ["users"],
        }
        result = node(state)
        assert result["generated_sql"].startswith('SELECT * FROM "users"')
        assert result["generated_sql"].endswith("LIMIT 25")
        assert result["sql_rationale"]
        assert result["sql_generation_prompt"]
        assert result["sql_generation_mode"] == "Deterministic"
        assert result["status"] == "validating"
    def test_node_failure_sets_failed_status(self):
        node = build_sql_generator_node(max_limit=-1)
        state = {
            "user_question": "Show all users",
            "schema_context": _schema_context(),
            "dialect": "sqlite",
        }
        result = node(state)
        assert result["generated_sql"] is None
        assert result["status"] == "failed"
        assert "failed to generate SQL" in result["error_message"]

    def test_node_llm_only_failure_sets_failed_status(self, monkeypatch):
        monkeypatch.setattr(
            sql_generator_agent_module,
            "_generate_sql_with_llm",
            lambda prompt: (None, "disabled"),
        )
        node = build_sql_generator_node(max_limit=25, generation_strategy="llm_only")
        state = {
            "user_question": "Show all users",
            "schema_context": _schema_context(),
            "dialect": "sqlite",
        }
        result = node(state)
        assert result["generated_sql"] is None
        assert result["status"] == "failed"
        assert "LLM-only generation failed" in result["error_message"]
