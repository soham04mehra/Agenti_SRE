from typing import TypedDict, List, Dict, Any, Optional, Literal

IncidentStatus = Literal[
    "investigating",
    "resolved",
    "insufficient_evidence",
    "unresolved_conflict",
    "failed"
]

class IncidentState(TypedDict):
    """
    Central IncidentState schema used by all 6 LangGraph workflow nodes.
    Stores structured investigation state, hypotheses, evidence, and confidence scores.
    """
    # Core Incident Information
    incident_id: str
    raw_description: str
    affected_service: Optional[str]
    symptom: Optional[str]
    timestamp: str
    severity: Optional[str]

    # Reasoning & Hypotheses State
    hypotheses: List[Dict[str, Any]]           # Active hypotheses being tested
    ruled_out_hypotheses: List[Dict[str, Any]] # Hypotheses disproven by evidence
    current_plan: Optional[str]               # Strategic plan for the current loop
    next_tool_calls: List[Dict[str, Any]]      # Diagnostic tools selected to run next

    # Evidence & Telemetry Summaries
    evidence: List[Dict[str, Any]]             # Classified evidence: supports, contradicts, neutral
    tools_called: List[str]                    # History of tool names executed
    raw_data_refs: List[Dict[str, Any]]        # References/links to large log or metric files
    similar_past_incidents: List[Dict[str, Any]] # Past incidents retrieved via RAG

    # Loop Control & Confidence Evaluation
    confidence_score: float                     # Deterministic evidence strength (0.0 to 1.0)
    iteration_count: int                        # Current investigation loop iteration count
    max_iterations: int                         # Max allowed loops (default: 3)
    status: IncidentStatus                      # "investigating", "resolved", "insufficient_evidence", "unresolved_conflict", "failed"
    degraded: bool                              # True if one or more diagnostic sources were unavailable
    final_report: Optional[Dict[str, Any]]      # Final generated Root Cause Analysis report
