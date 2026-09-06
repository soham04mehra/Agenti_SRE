import json
from agent.graph import incident_agent_app

# Initial input state for test incident
initial_state = {
    "incident_id": "test_inc_001",
    "raw_description": "Payment service is failing with high error rates and DB connection timeouts.",
    "affected_service": None,
    "symptom": None,
    "timestamp": "2026-09-06T00:00:00Z",
    "severity": "HIGH",
    "hypotheses": [],
    "ruled_out_hypotheses": [],
    "current_plan": None,
    "next_tool_calls": [],
    "evidence": [],
    "tools_called": [],
    "raw_data_refs": [],
    "similar_past_incidents": [],
    "confidence_score": 0.0,
    "iteration_count": 0,
    "max_iterations": 3,
    "status": "investigating",
    "final_report": None
}

print("🚀 Starting LangGraph Agent Investigation Loop...")
final_output = incident_agent_app.invoke(initial_state)

print("\n================ FINAL INCIDENT STATE ================")
print(f"Status: {final_output.get('status')}")
print(f"Confidence Score: {final_output.get('confidence_score')}")
print(f"Iteration Count: {final_output.get('iteration_count')}")
print(f"Tools Called: {final_output.get('tools_called')}")

print("\n================ FINAL RCA REPORT ================")
print(json.dumps(final_output.get("final_report"), indent=2))
