from langgraph.graph import StateGraph, START, END
from agent.state import IncidentState
from agent.nodes import (
    understand_incident,
    plan_investigation,
    execute_tools,
    observe_evidence,
    evaluate_confidence_node,
    generate_report
)

def route_after_confidence(state: IncidentState) -> str:
    """
    Router function that decides whether to loop back or report.
    Returns:
      - 'generate_report': If status in terminal states ('resolved', 'insufficient_evidence', 'unresolved_conflict', 'failed').
      - 'replan': If status == 'investigating' and iterations remain (loops back to plan_investigation).
    """
    status = state.get("status")
    if status in ["resolved", "sufficient_confidence", "insufficient_evidence", "unresolved_conflict", "failed"]:
        return "generate_report"
    return "replan"

def build_graph():
    """Build and compile the 6-node LangGraph incident investigation graph."""
    workflow = StateGraph(IncidentState)

    # 1. Register all 6 nodes
    workflow.add_node("understand_incident", understand_incident)
    workflow.add_node("plan_investigation", plan_investigation)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("observe_evidence", observe_evidence)
    workflow.add_node("evaluate_confidence", evaluate_confidence_node)
    workflow.add_node("generate_report", generate_report)

    # 2. Add Fixed Sequential Edges
    workflow.add_edge(START, "understand_incident")
    workflow.add_edge("understand_incident", "plan_investigation")
    workflow.add_edge("plan_investigation", "execute_tools")
    workflow.add_edge("execute_tools", "observe_evidence")
    workflow.add_edge("observe_evidence", "evaluate_confidence")

    # 3. Add Conditional Routing Edge (Replan vs Report)
    workflow.add_conditional_edges(
        "evaluate_confidence",
        route_after_confidence,
        {
            "replan": "plan_investigation",        # Loop back to plan_investigation
            "generate_report": "generate_report"   # Finish and write RCA report
        }
    )

    # 4. Final Exit Edge
    workflow.add_edge("generate_report", END)

    return workflow.compile()

# Create runnable application
incident_agent_app = build_graph()
