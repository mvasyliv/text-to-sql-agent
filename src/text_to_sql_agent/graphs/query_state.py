"""LangGraph state definition for the DB query orchestration workflow."""

from typing import Annotated, TypedDict


def _append(existing: list, new: list | str) -> list:
    """LangGraph-compatible list reducer: appends new items to existing."""
    if isinstance(new, list):
        return existing + new
    return existing + [new]


class QueryState(TypedDict):
    """Typed state for the end-to-end DB query LangGraph workflow.

    Tracks one user-initiated query from natural-language input through
    SQL generation, validation, security check, human approval, MCP
    execution, and optional analytics / export steps.

    Fields are organised into logical groups mirroring the pipeline stages.
    """

    # -------------------------------------------------------------------
    # Session context
    # -------------------------------------------------------------------
    user_id: str
    """Stable identifier of the user who initiated this query."""

    conversation_id: str
    """Conversation this query belongs to."""

    message_id: str
    """Identifier of the triggering user message."""

    # -------------------------------------------------------------------
    # Input
    # -------------------------------------------------------------------
    user_question: str
    """Raw natural-language question from the user."""

    database_id: str
    """Target database identifier passed to the MCP server."""

    dialect: str
    """SQL dialect expected by the target database (sqlite, postgresql, …)."""

    selected_tables: list[str] | None
    """Optional list of selected table names used for schema and prompt scoping."""

    # -------------------------------------------------------------------
    # Schema context — filled by schema context agent
    # -------------------------------------------------------------------
    schema_context: str | None
    """Formatted schema description supplied to the SQL generator."""

    # -------------------------------------------------------------------
    # SQL generation — filled by SQL generator agent
    # -------------------------------------------------------------------
    generated_sql: str | None
    """SQL produced by the generator agent."""

    sql_generation_prompt: str | None
    """Rendered SQL generation prompt text used for debugging and traceability."""

    sql_generation_mode: str | None
    """Visible SQL generation mode label: LLM | Few-shot fallback | Deterministic."""

    sql_rationale: str | None
    """Brief explanation of why this SQL was generated."""

    llm_status: str | None
    """LLM generation status for this turn (ok/disabled/missing_api_key/...)."""

    llm_user_notice: str | None
    """Optional user-facing notice when LLM is unavailable and fallback is used."""

    # -------------------------------------------------------------------
    # Validation — filled by syntax validator agent
    # -------------------------------------------------------------------
    syntax_valid: bool | None
    """True if the generated SQL passed syntax validation."""

    syntax_errors: Annotated[list[str], _append]
    """Syntax error messages collected during validation."""

    # -------------------------------------------------------------------
    # Security — filled by security guard agent
    # -------------------------------------------------------------------
    security_approved: bool | None
    """True if the SQL passed security policy checks."""

    security_violations: Annotated[list[str], _append]
    """Security policy violations detected in the SQL."""

    # -------------------------------------------------------------------
    # Human approval — updated by human approval gate
    # -------------------------------------------------------------------
    human_approved: bool | None
    """True=approved, False=rejected, None=pending."""

    edited_sql: str | None
    """SQL edited by the human during the approval step, if any."""

    # -------------------------------------------------------------------
    # Execution — filled by query execution agent
    # -------------------------------------------------------------------
    execution_result: dict | None
    """Raw result payload from MCP execution: rows, columns, row_count."""

    execution_error: str | None
    """Error message if execution failed."""

    # -------------------------------------------------------------------
    # Post-processing — filled by analytics / export agents
    # -------------------------------------------------------------------
    chart_spec: dict | None
    """Plotly-compatible chart specification produced by analytics agent."""

    export_path: str | None
    """File path or download reference produced by export agent."""

    insight_text: str | None
    """Natural-language conclusions produced by insight agent."""

    # -------------------------------------------------------------------
    # Control flow
    # -------------------------------------------------------------------
    status: str
    """Workflow status: pending | validating | awaiting_approval | executing
    | post_processing | done | failed | cancelled."""

    error_message: str | None
    """Human-readable error if status is failed."""

    # -------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------
    log_messages: Annotated[list[str], _append]
    """Structured log entries appended by each node."""

    agent_events: Annotated[list[dict], _append]
    """Serialised AgentEvent dicts emitted by each pipeline node for audit."""
