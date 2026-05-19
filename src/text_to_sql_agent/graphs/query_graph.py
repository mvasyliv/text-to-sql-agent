"""LangGraph orchestration graph for the DB query pipeline.

Wires the following steps in order:
  schema_context -> sql_generator -> syntax_validator -> security_guard
    -> human_approval -> query_executor -> analytics -> insights -> export -> done

Each node is a thin stub that updates QueryState. Real agent logic
will be plugged in by the dedicated agent tasks (T-2026-05-18-042 … 049).

Human approval uses LangGraph interrupt() to pause execution and wait
for an explicit user decision (approve / reject / edit) before proceeding.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from text_to_sql_agent.agents.analytics_agent import build_analytics_node
from text_to_sql_agent.agents.human_approval_agent import build_human_approval_node
from text_to_sql_agent.agents.export_agent import build_export_node
from text_to_sql_agent.agents.insights_agent import build_insights_node
from text_to_sql_agent.agents.query_execution_agent import build_query_execution_node
from text_to_sql_agent.agents.schema_context_agent import build_schema_context_node
from text_to_sql_agent.agents.security_guard_agent import build_security_guard_node
from text_to_sql_agent.agents.sql_generator_agent import build_sql_generator_node
from text_to_sql_agent.agents.syntax_validator_agent import build_syntax_validator_node
from text_to_sql_agent.graphs.query_state import QueryState
from text_to_sql_agent.services.audit_trail import make_agent_event

# Schema context node is built with a default connection config.
# Override by passing a custom node to build_query_graph().
_DEFAULT_CONNECTION_CONFIG: dict = {}

node_schema_context = build_schema_context_node(_DEFAULT_CONNECTION_CONFIG)
node_sql_generator = build_sql_generator_node()
node_syntax_validator = build_syntax_validator_node()
node_security_guard = build_security_guard_node()
node_human_approval = build_human_approval_node()
node_analytics = build_analytics_node()
node_insights = build_insights_node()
node_export = build_export_node()


def node_done(state: QueryState) -> dict:
    """Mark the workflow as completed."""
    return {
        "status": "done",
        "log_messages": ["done: workflow completed"],
        "agent_events": [
            make_agent_event(
                agent="workflow",
                event_type="workflow_done",
                status="ok",
                user_id=state.get("user_id"),
                conversation_id=state.get("conversation_id"),
                message_id=state.get("message_id"),
            )
        ],
    }


def node_failed(state: QueryState) -> dict:
    """Mark the workflow as failed."""
    return {
        "status": "failed",
        "log_messages": ["failed: workflow terminated with error"],
        "agent_events": [
            make_agent_event(
                agent="workflow",
                event_type="workflow_failed",
                status="error",
                user_id=state.get("user_id"),
                conversation_id=state.get("conversation_id"),
                message_id=state.get("message_id"),
                metadata={"error_message": state.get("error_message")},
            )
        ],
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
    execution_node = build_query_execution_node(connection_config)

    builder = StateGraph(QueryState)

    # Nodes
    builder.add_node("schema_context", schema_node)
    builder.add_node("sql_generator", node_sql_generator)
    builder.add_node("syntax_validator", node_syntax_validator)
    builder.add_node("security_guard", node_security_guard)
    builder.add_node("human_approval", node_human_approval)
    builder.add_node("query_executor", execution_node)
    builder.add_node("analytics", node_analytics)
    builder.add_node("insights", node_insights)
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
    builder.add_edge("analytics", "insights")
    builder.add_edge("insights", "export")
    builder.add_edge("export", "done")
    builder.add_edge("done", END)
    builder.add_edge("failed", END)

    return builder.compile(checkpointer=checkpointer, interrupt_before=["human_approval"])
