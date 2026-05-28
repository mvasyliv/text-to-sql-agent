"""SQL generator agent for read-only query synthesis.

Builds deterministic SQL from:
- user natural-language question
- formatted schema context from schema_context_agent

The agent intentionally avoids write operations and emits only SELECT queries.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from text_to_sql_agent.prompts import build_sql_generation_prompt
from text_to_sql_agent.prompts import get_few_shot_examples_for_tables
from text_to_sql_agent.services.audit_trail import make_agent_event


_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_COUNT_HINTS = {"count", "how", "many", "total", "number"}
_LIST_HINTS = {"list", "show", "all", "display", "give", "find", "get"}
_MATCH_IGNORE_TOKENS = {
    "list",
    "show",
    "all",
    "display",
    "give",
    "find",
    "get",
    "me",
    "please",
    "the",
}
_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
_COUNTRY_CODE_RE = re.compile(r"\b[A-Z]{2}\b")
_NUMBER_RE = re.compile(r"\b\d+\b")
_BLOCKED_SQL_TOKENS = ("insert", "update", "delete", "drop", "alter", "truncate")
_LLM_UNAVAILABLE_STATUSES = {"disabled", "missing_api_key", "client_unavailable", "error"}


@dataclass(frozen=True, slots=True)
class SQLGenerationResult:
    """Structured output of SQL generation."""

    sql: str
    rationale: str
    table_used: str | None
    intent: str
    prompt: str = ""
    few_shot_count: int = 0
    llm_status: str = "not_attempted"
    llm_user_notice: str | None = None


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _quote_identifier(name: str, dialect: str) -> str:
    """Quote SQL identifiers safely for supported dialects."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")

    # SQLite and PostgreSQL accept ANSI double-quote escaping.
    if dialect in {"sqlite", "postgres", "postgresql"}:
        return f'"{name}"'
    return name


def _parse_schema_context(schema_context: str) -> dict[str, list[str]]:
    """Parse TABLE/COLUMN lines from formatted schema context text."""
    tables: dict[str, list[str]] = {}
    current_table: str | None = None

    for raw_line in schema_context.splitlines():
        line = raw_line.strip()
        if line.startswith("TABLE "):
            table_name = line.removeprefix("TABLE ").strip()
            if table_name:
                current_table = table_name
                tables.setdefault(current_table, [])
            continue

        if current_table is None:
            continue

        # Column lines are formatted like: "  id integer [PK]"
        if line and not line.startswith("FK:"):
            col_name = line.split(" ", 1)[0].strip()
            if _IDENTIFIER_RE.match(col_name):
                tables[current_table].append(col_name)

    return tables


def _choose_table(question_tokens: list[str], schema_map: dict[str, list[str]]) -> str | None:
    if not schema_map:
        return None

    for table in schema_map:
        low = table.lower()
        singular = low[:-1] if low.endswith("s") else low
        if low in question_tokens or singular in question_tokens:
            return table

    return next(iter(schema_map))


def _detect_intent(tokens: list[str]) -> str:
    if any(token in _COUNT_HINTS for token in tokens):
        return "count"
    if any(token in _LIST_HINTS for token in tokens):
        return "list"
    return "list"


def _resolve_openai_api_key() -> str | None:
    for key_name in ("OPENAI_API_KEY", "OPENAI_KEY", "OPENAI_TOKEN", "LLM_API_KEY"):
        raw_value = os.getenv(key_name)
        if not raw_value:
            continue
        value = raw_value.strip().strip('"').strip("'")
        if value:
            return value
    return None


def _extract_sql_candidate(text: str) -> str:
    fenced = _SQL_FENCE_RE.search(text)
    if fenced:
        return fenced.group(1).strip()
    return text.strip()


def _is_read_only_sql(sql: str) -> bool:
    normalized = sql.strip().lower()
    if not normalized:
        return False
    if not (normalized.startswith("select") or normalized.startswith("with") or normalized.startswith("explain")):
        return False
    return all(f"{token} " not in normalized for token in _BLOCKED_SQL_TOKENS)


def _is_llm_generation_enabled() -> bool:
    raw = os.getenv("SQL_GENERATOR_LLM_ENABLED", "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _normalized_match_tokens(text: str) -> set[str]:
    return {token for token in _tokenize(text) if token not in _MATCH_IGNORE_TOKENS}


def _extract_country_codes(text: str) -> set[str]:
    upper_text = text.upper()
    return {code for code in _COUNTRY_CODE_RE.findall(upper_text)}


def _extract_numbers(text: str) -> set[str]:
    return set(_NUMBER_RE.findall(text))


def _normalize_text_for_match(text: str) -> str:
    return " ".join(_tokenize(text))


def _few_shot_match_score(user_question: str, example_input: str) -> float:
    question_tokens = _normalized_match_tokens(user_question)
    example_tokens = _normalized_match_tokens(example_input)
    if not question_tokens or not example_tokens:
        return 0.0

    overlap = len(question_tokens & example_tokens) / len(example_tokens)
    score = overlap

    normalized_question = _normalize_text_for_match(user_question)
    normalized_example = _normalize_text_for_match(example_input)
    if normalized_question == normalized_example:
        score += 2.0
    elif normalized_example in normalized_question:
        score += 0.75

    question_countries = _extract_country_codes(user_question)
    example_countries = _extract_country_codes(example_input)
    if question_countries and example_countries:
        if question_countries == example_countries:
            score += 0.9
        elif question_countries & example_countries:
            score += 0.35
        else:
            score -= 0.4

    question_numbers = _extract_numbers(user_question)
    example_numbers = _extract_numbers(example_input)
    if question_numbers and example_numbers:
        if question_numbers == example_numbers:
            score += 0.5
        elif question_numbers & example_numbers:
            score += 0.2

    return score


def _select_few_shot_sql(user_question: str, few_shot_examples) -> str | None:
    """Choose the most relevant few-shot SQL with exact/entity-aware scoring."""

    best_query: str | None = None
    best_score = -1.0

    for example in few_shot_examples:
        score = _few_shot_match_score(user_question, example.input)
        if score > best_score:
            best_score = score
            best_query = example.query

    if best_query and best_score >= 0.8:
        return best_query
    return None


def _generate_sql_with_llm(prompt: str) -> tuple[str | None, str]:
    api_key = _resolve_openai_api_key()
    if not _is_llm_generation_enabled():
        return None, "disabled"
    if not api_key:
        return None, "missing_api_key"

    try:
        from langchain_openai import ChatOpenAI
    except Exception:  # noqa: BLE001
        return None, "client_unavailable"

    try:
        llm = ChatOpenAI(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )
        response = llm.invoke(
            [
                (
                    "system",
                    "You generate exactly one read-only SQL query. "
                    "Return only SQL text, without commentary.",
                ),
                ("human", prompt),
            ]
        )
        content = getattr(response, "content", "")
        if isinstance(content, list):
            content = "\n".join(str(item) for item in content)
        sql = _extract_sql_candidate(str(content))
        if not _is_read_only_sql(sql):
            return None, "unsafe_output"
        return sql, "ok"
    except Exception:  # noqa: BLE001
        return None, "error"


def _llm_notice_for_status(status: str) -> str | None:
    if status in _LLM_UNAVAILABLE_STATUSES:
        return (
            "LLM is unavailable right now. "
            "Using deterministic SQL generation with table-aware few-shot fallback."
        )
    return None


def _resolve_generation_mode(intent: str) -> str:
    if intent == "llm":
        return "LLM"
    if intent == "few_shot":
        return "Few-shot fallback"
    return "Deterministic"


def _generate_deterministic_sql(
    *,
    user_question: str,
    schema_context: str,
    dialect: str,
    max_limit: int,
) -> tuple[str, str, str | None, str]:
    tokens = _tokenize(user_question)
    schema_map = _parse_schema_context(schema_context)
    table = _choose_table(tokens, schema_map)
    intent = _detect_intent(tokens)

    if table is None:
        return (
            "SELECT 1 AS result LIMIT 1",
            "No tables were detected in schema context; returning safe probe query.",
            None,
            "probe",
        )

    quoted_table = _quote_identifier(table, dialect)
    if intent == "count":
        return (
            f"SELECT COUNT(*) AS row_count FROM {quoted_table}",
            f"Detected counting intent; counting rows in table '{table}'.",
            table,
            intent,
        )

    return (
        f"SELECT * FROM {quoted_table} LIMIT {max_limit}",
        (
            f"Detected listing intent; selecting rows from table '{table}' "
            f"with LIMIT {max_limit} for safe preview."
        ),
        table,
        intent,
    )


def generate_read_only_sql(
    user_question: str,
    schema_context: str,
    *,
    dialect: str = "sqlite",
    max_limit: int = 100,
    selected_tables: list[str] | None = None,
) -> SQLGenerationResult:
    """Generate a read-only SQL query from question + schema context.

    The generator is deterministic and intentionally conservative for MVP.
    """
    if max_limit <= 0:
        raise ValueError("max_limit must be greater than zero")

    prompt = build_sql_generation_prompt(
        user_request=user_question,
        schema_context=schema_context,
        dialect=dialect,
        selected_tables=selected_tables,
    )
    few_shot_examples = get_few_shot_examples_for_tables(dialect, selected_tables)
    llm_sql, llm_status = _generate_sql_with_llm(prompt)
    llm_notice = _llm_notice_for_status(llm_status)
    if llm_sql:
        return SQLGenerationResult(
            sql=llm_sql,
            rationale="Generated via LLM using schema context and few-shot prompt examples.",
            table_used=None,
            intent="llm",
            prompt=prompt,
            few_shot_count=len(few_shot_examples),
            llm_status=llm_status,
            llm_user_notice=llm_notice,
        )

    matched_few_shot_sql = _select_few_shot_sql(user_question, few_shot_examples)
    if matched_few_shot_sql and _is_read_only_sql(matched_few_shot_sql):
        return SQLGenerationResult(
            sql=matched_few_shot_sql,
            rationale="Matched a table-aware few-shot example and reused its SQL pattern.",
            table_used=None,
            intent="few_shot",
            prompt=prompt,
            few_shot_count=len(few_shot_examples),
            llm_status=llm_status,
            llm_user_notice=llm_notice,
        )

    sql, rationale, table, intent = _generate_deterministic_sql(
        user_question=user_question,
        schema_context=schema_context,
        dialect=dialect,
        max_limit=max_limit,
    )

    return SQLGenerationResult(
        sql=sql,
        rationale=rationale,
        table_used=table,
        intent=intent,
        prompt=prompt,
        few_shot_count=len(few_shot_examples),
        llm_status=llm_status,
        llm_user_notice=llm_notice,
    )


def build_sql_generator_node(*, max_limit: int = 100):
    """Return a LangGraph-compatible SQL generator node."""

    def node(state: dict) -> dict:
        question = state["user_question"]
        schema_context = state.get("schema_context") or ""
        dialect = state.get("dialect", "sqlite")
        selected_tables = state.get("selected_tables")
        try:
            result = generate_read_only_sql(
                question,
                schema_context,
                dialect=dialect,
                max_limit=max_limit,
                selected_tables=selected_tables,
            )
            return {
                "generated_sql": result.sql,
                "sql_generation_prompt": result.prompt,
                "sql_generation_mode": _resolve_generation_mode(result.intent),
                "sql_rationale": result.rationale,
                "llm_status": result.llm_status,
                "llm_user_notice": result.llm_user_notice,
                "status": "validating",
                "log_messages": [
                    "sql_generator: SQL generated"
                    f" (intent={result.intent}, table={result.table_used}, "
                    f"few_shot_count={result.few_shot_count}, "
                    f"llm_status={result.llm_status})"
                ],
                "agent_events": [
                    make_agent_event(
                        agent="sql_generator",
                        event_type="sql_generated",
                        status="ok",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={
                            "intent": result.intent,
                            "table_used": result.table_used,
                            "few_shot_count": result.few_shot_count,
                            "selected_tables": selected_tables,
                            "llm_status": result.llm_status,
                        },
                    )
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "generated_sql": None,
                "sql_rationale": None,
                "status": "failed",
                "error_message": f"sql_generator: failed to generate SQL - {exc}",
                "log_messages": [f"sql_generator: ERROR - {exc}"],
                "agent_events": [
                    make_agent_event(
                        agent="sql_generator",
                        event_type="sql_generated",
                        status="error",
                        user_id=state.get("user_id"),
                        conversation_id=state.get("conversation_id"),
                        message_id=state.get("message_id"),
                        metadata={"error": str(exc)},
                    )
                ],
            }

    return node
