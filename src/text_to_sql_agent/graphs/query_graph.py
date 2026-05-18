"""LangGraph orchestration graph for the DB query pipeline.

Wires the following steps in order:
  schema_context -> sql_generator -> syntax_validator -> security_guard
  -> human_approval -> query_executor -> [analytics | export | done]

Each node is a thin stub that updates QueryState. Real agent logic
will be plugged in by the dedicated agent tasks (T-2026-05-18-042 … 049).

Human approval uses LangGraph interrupt() to pause execution and wait
for an explicit user decision (approve / reject / edit) before proceeding.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.types import interrupt

from text_to_sql_agent.agents.schema_context_agent import build_schema_context_node
from text_to_sql_agent.graphs.query_state import QueryState

# Schema context node is built with a default connection config.
# Override by passing a custom node to build_query_graph().
_DEFAULT_CONNECTION_CONFIG: dict = {}

node_schema_context = build_schema_context_node(_DEFAULT_CONNECTION_CONFIG)


# ---------------------------------------------------------------------------
# Node implementations (stubs — replaced by real agents in later tasks)
# ---------------------------------------------------------------------------


def node_sql_generator(state: QueryState) -> dict:
    """Generate a read-only SQL query from the user question and schema context."""
    return {
        "generated_sql": f"SELECT * FROM ... -- generated for: {state['user_question']}",
        "sql_rationale": "stub rationale",
        "log_messages": ["sql_generator: SQL generated (stub)"],
    }


def node_syntax_validator(state: QueryState) -> dict:
    """Validate SQL syntax before security and approval checks."""
    sql = state.get("generated_sql") or ""
    valid = bool(sql.strip())
    return {
        "syntax_valid": valid,
        "syntax_errors": [] if valid else ["Empty SQL"],
        "log_messages": [f"syntax_validator: valid={valid}"],
    }


def node_security_guard(state: QueryState) -> dict:
    """Enforce read-only policy and block suspicious SQL patterns."""
    sql = (state.get("generated_sql") or "").strip().lower()
    blocked_keywords = {"drop", "delete", "insert", "update", "truncate", "alter", "create"}
    violations = [kw for kw in blocked_keywords if kw in sql]
    approved = len(violations) == 0
    return {
        "security_approved": approved,
        "security_violations": violations,
        "log_messages": [f"security_guard: approved={approved}, violations={violations}"],
    }


def node_human_approval(state: QueryState) -> dict:
    """Pause execution and wait for explicit human approval of the SQL.

    Uses LangGraph interrupt() to suspend the graph. The caller resumes
    the graph by invoking it with Command(resume=<decision>) where decision
    is one of: 'approve', 'reject', or {'edit': '<new_sql>'}.
    """
    sql = state.get("edited_sql") or state.get("generated_sql") or ""
    decision = interrupt(
        {
            "prompt": "Review the SQL query below and choose an action.",
            "sql": sql,
            "actions": ["approve", "reject", "edit"],
        }
    )

    if isinstance(decision, dict) and "edit" in decision:
        return {
            "human_approved": True,
            "edited_sql": decision["edit"],
            "status": "executing",
            "log_messages": ["human_approval: SQL edited and approved by user"],
        }
    if decision == "approve":
        return {
            "human_approved": True,
            "status": "executing",
            "log_messages": ["human_approval: SQL approved by user"],
        }
    # reject or unexpected
    return {
        "human_approved": False,
        "status": "cancelled",
        "log_messages": [f"human_approval: rejected by user (decision={decision!r})"],
    }


def node_query_executor(state: QueryState) -> dict:
    """Execute the approved SQL via the MCP database server."""
    sql = state.get("edited_sql") or state.get("generated_sql") or ""
    # Stub: real implementation calls MCP execute-query tool
    return {
        "execution_result": {"rows": [], "columns": [], "row_count": 0, "sql": sql},
        "execution_error": None,
        "status": "post_processing",
        "log_messages": ["query_executor: query executed via MCP (stub)"],
    }


def node_analytics(state: QueryState) -> dict:
    """Build a one-shot chart specification from the execution result."""
    return {
        "chart_spec": {"type": "bar", "data": []},
        "log_messages": ["analytics: chart spec produced (stub)"],
    }


def node_export(state: QueryState) -> dict:
    """Export the execution result to a downloadable file."""
    return {
        "export_path": "/tmp/export.csv",
        "log_messages": ["export: file written (stub)"],
    }


def node_done(state: QueryState) -> dict:
    """Mark the workflow as completed."""
    return {
        "status": "done",
        "log_messages": ["done: workflow completed"],
    }


def node_failed(state: QueryState) -> dict:
    """Mark the workflow as failed."""
    return {
        "status": "failed",
        "log_messages": ["failed: workflow terminated with error"],
    }


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------


def _route_after_syntax(state: QueryState) -> str:
    if state.get("syntax_valid"):
        return "security_guard"
    return "failed"


def _route_after_security(state: QueryState) -> str:
    if state.get("security_approved"):
        return "human_approval"
    return "failed"


def _route_after_approval(state: QueryState) -> str:
    if state.get("human_approved"):
        return "query_executor"
    return "failed"


def _route_after_execution(state: QueryState) -> str:
    if state.get("execution_error"):
        return "failed"
    return "analytics"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_query_graph(checkpointer=None, connection_config: dict | None = None):
    """Compile and return the DB query orchestration graph.

    Args:
        checkpointer: Optional LangGraph checkpointer for persistence.
                      Defaults to in-memory MemorySaver when None.
        connection_config: Optional connection parameters forwarded to the
                           schema context node (e.g. {"path": "/data/db.sqlite"}).
                           When None, the default empty-config stub is used.

    Returns:
        A compiled LangGraph CompiledGraph ready for invocation.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    schema_node = (
        build_schema_context_node(connection_config)
        if connection_config is not None
        else node_schema_context
    )

    builder = StateGraph(QueryState)

    # Nodes
    builder.add_node("schema_context", schema_node)
    builder.add_node("sql_generator", node_sql_generator)
    builder.add_node("syntax_validator", node_syntax_validator)
    builder.add_node("security_guard", node_security_guard)
    builder.add_node("human_approval", node_human_approval)
    builder.add_node("query_executor", node_query_executor)
    builder.add_node("analytics", node_analytics)
    builder.add_node("export", node_export)
    builder.add_node("done", node_done)
    builder.add_node("failed", node_failed)

    # Edges
    builder.add_edge(START, "schema_context")
    builder.add_edge("schema_context", "sql_generator")
    builder.add_edge("sql_generator", "syntax_validator")
    builder.add_conditional_edges("syntax_validator", _route_after_syntax)
    builder.add_conditional_edges("security_guard", _route_after_security)
    builder.add_conditional_edges("human_approval", _route_after_approval)
    builder.add_conditional_edges("query_executor", _route_after_execution)
    builder.add_edge("analytics", "export")
    builder.add_edge("export", "done")
    builder.add_edge("done", END)
    builder.add_edge("failed", END)

    return builder.compile(checkpointer=checkpointer, interrupt_before=["human_approval"])
