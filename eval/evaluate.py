import json
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import GROUND_TRUTHS_DIR
from agent.graph import incident_agent_app
from database.repository import save_incident_state

def evaluate_agent_benchmark() -> dict:
    """
    Runs the agent against all 24 ground-truth incidents and measures metrics.
    """
    gt_files = sorted(list(GROUND_TRUTHS_DIR.glob("eval_inc_*.json")))
    if not gt_files:
        print("⚠️ No ground-truth files found. Run 'python eval/generate_dataset.py' first.")
        return {}

    total_incidents = len(gt_files)
    correct_root_cause = 0
    false_confidence_count = 0
    total_evidence_expected = 0
    total_evidence_retrieved = 0
    total_evidence_relevant = 0

    total_iterations = 0
    total_latency_sec = 0.0

    print(f"🚀 Starting Evaluation Benchmark on {total_incidents} Ground-Truth Incidents...\n")

    for gt_file in gt_files:
        with open(gt_file, "r") as f:
            gt = json.load(f)

        # Prepare initial state
        initial_state = {
            "incident_id": gt["incident_id"],
            "raw_description": gt["raw_description"],
            "affected_service": gt["affected_service"],
            "symptom": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
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

        start_time = time.time()
        result_state = incident_agent_app.invoke(initial_state)
        latency = time.time() - start_time
        total_latency_sec += latency

        save_incident_state(result_state)

        # Evaluate metrics
        iterations = result_state.get("iteration_count", 1)
        total_iterations += iterations
        final_report = result_state.get("final_report", {})
        conf_score = result_state.get("confidence_score", 0.0)

        # 1. Root Cause Accuracy Check
        reported_cause = str(final_report.get("root_cause_summary") or final_report.get("root_cause") or "").lower()
        fault_type = gt["fault_type"].lower()
        
        is_correct_rc = False
        if fault_type == "db_pool_exhaustion" and ("db" in reported_cause or "pool" in reported_cause or "connection" in reported_cause):
            is_correct_rc = True
        elif fault_type == "bad_deployment" and ("deployment" in reported_cause or "config" in reported_cause or "url" in reported_cause):
            is_correct_rc = True
        elif fault_type == "memory_leak" and ("memory" in reported_cause or "heap" in reported_cause):
            is_correct_rc = True
        elif fault_type == "downstream_timeout" and ("timeout" in reported_cause or "gateway" in reported_cause):
            is_correct_rc = True

        if is_correct_rc:
            correct_root_cause += 1

        # 2. False Confidence Check
        if conf_score >= 0.75 and not is_correct_rc:
            false_confidence_count += 1

        # 3. Evidence Retrieval Recall & Precision
        retrieved_evidence = result_state.get("evidence", [])
        total_evidence_expected += len(gt["expected_evidence"])
        total_evidence_retrieved += len(retrieved_evidence)
        
        relevant_count = len([e for e in retrieved_evidence if e.get("classification") == "supports"])
        total_evidence_relevant += relevant_count

    # Calculate final aggregate percentage metrics
    rc_accuracy_pct = round((correct_root_cause / total_incidents) * 100, 2)
    recall_pct = round((total_evidence_relevant / max(1, total_evidence_expected)) * 100, 2)
    precision_pct = round((total_evidence_relevant / max(1, total_evidence_retrieved)) * 100, 2)
    false_conf_pct = round((false_confidence_count / total_incidents) * 100, 2)
    avg_iterations = round(total_iterations / total_incidents, 2)
    avg_latency_sec = round(total_latency_sec / total_incidents, 2)

    metrics_report = {
        "total_incidents_evaluated": total_incidents,
        "root_cause_accuracy_pct": rc_accuracy_pct,
        "retrieval_recall_pct": recall_pct,
        "retrieval_precision_pct": precision_pct,
        "false_confidence_rate_pct": false_conf_pct,
        "avg_iterations_per_incident": avg_iterations,
        "avg_latency_seconds": avg_latency_sec,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    print("\n================ EVALUATION HARNESS BENCHMARK RESULTS ================")
    print(json.dumps(metrics_report, indent=2))

    return metrics_report

if __name__ == "__main__":
    evaluate_agent_benchmark()
