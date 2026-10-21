import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.graph import incident_agent_app

def evaluate_suite(dataset_dir: Path, suite_name: str = "Development Suite") -> dict:
    """
    Evaluates the agent workflow against a structured robustness dataset.
    Calculates exact counts and formal metrics defined in EVALUATION.md.
    """
    case_files = sorted(list(dataset_dir.glob("*.json")))
    if not case_files:
        print(f"⚠️ No cases found in {dataset_dir}")
        return {}

    total_cases = len(case_files)
    diagnostic_cases = 0
    correct_diagnostic = 0

    abstention_cases = 0
    correct_abstention = 0
    false_confidence = 0

    total_citations = 0
    valid_citations = 0

    total_iterations = 0
    total_latency_sec = 0.0

    results = []

    print(f"\n================ RUNNING {suite_name.upper()} ({total_cases} CASES) ================")
    print(f"Dataset path: {dataset_dir}\n")

    for case_file in case_files:
        with open(case_file, "r") as f:
            case = json.load(f)

        case_id = case["case_id"]
        category = case["category"]
        expected_status = case["expected_status"]
        allowed_causes = [c.lower() for c in case.get("allowed_root_causes", [])]

        initial_state = {
            "incident_id": case_id,
            "raw_description": case["incident_description"],
            "affected_service": case.get("affected_service", "payment_service"),
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
        final_state = incident_agent_app.invoke(initial_state)
        latency = time.time() - start_time

        total_latency_sec += latency
        iterations = final_state.get("iteration_count", 1)
        total_iterations += iterations

        actual_status = final_state.get("status", "unknown")
        final_report = final_state.get("final_report", {}) or {}
        reported_cause = str(final_report.get("root_cause_summary") or "").lower()

        # Categorize evaluation criteria
        is_diagnostic_expected = category in ["clear_diagnosis", "noisy_evidence"]

        if is_diagnostic_expected:
            diagnostic_cases += 1
            # Check if diagnosis matches allowed causes
            matches_cause = any(ac in reported_cause for ac in allowed_causes)
            if matches_cause and actual_status in ["sufficient_confidence", "resolved"]:
                correct_diagnostic += 1
                outcome = "PASS (Diagnosed)"
            else:
                outcome = f"FAIL (Expected {allowed_causes}, got '{reported_cause[:40]}...')"
        else:
            abstention_cases += 1
            # Expected to abstain / not declare premature resolution
            if actual_status in ["insufficient_evidence", "unresolved_conflict", "failed"]:
                correct_abstention += 1
                outcome = "PASS (Abstained)"
            else:
                # System declared resolved / sufficient confidence when it shouldn't have
                false_confidence += 1
                outcome = f"FAIL (False Confidence: Declared {actual_status} with '{reported_cause[:30]}')"

        # Citation validation (Level 1: Existence)
        citations = final_state.get("evidence", [])
        for cit in citations:
            total_citations += 1
            cit_path = cit.get("citation", "")
            # If citation has a line number like :L66, strip it
            clean_path = cit_path.split(":")[0]
            if (BASE_DIR / clean_path).exists() or clean_path.startswith("deployments/") or clean_path.startswith("supabase/"):
                valid_citations += 1

        print(f"[{case_id}] Category: {category:<25} Status: {actual_status:<22} Outcome: {outcome}")

        results.append({
            "case_id": case_id,
            "category": category,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "reported_cause": reported_cause,
            "iterations": iterations,
            "latency_sec": round(latency, 4),
            "outcome": outcome
        })

    # Metric calculations
    rca_ratio = f"{correct_diagnostic} / {diagnostic_cases}" if diagnostic_cases > 0 else "N/A"
    rca_pct = round((correct_diagnostic / diagnostic_cases) * 100, 2) if diagnostic_cases > 0 else 0.0

    car_ratio = f"{correct_abstention} / {abstention_cases}" if abstention_cases > 0 else "N/A"
    car_pct = round((correct_abstention / abstention_cases) * 100, 2) if abstention_cases > 0 else 0.0

    fcr_ratio = f"{false_confidence} / {abstention_cases}" if abstention_cases > 0 else "N/A"
    fcr_pct = round((false_confidence / abstention_cases) * 100, 2) if abstention_cases > 0 else 0.0

    cvr_ratio = f"{valid_citations} / {total_citations}" if total_citations > 0 else "N/A"
    cvr_pct = round((valid_citations / total_citations) * 100, 2) if total_citations > 0 else 0.0

    avg_iterations = round(total_iterations / total_cases, 2)
    avg_latency = round(total_latency_sec / total_cases, 4)

    summary = {
        "suite_name": suite_name,
        "total_cases": total_cases,
        "diagnostic_cases_count": diagnostic_cases,
        "root_cause_accuracy": {"ratio": rca_ratio, "percentage": rca_pct},
        "abstention_cases_count": abstention_cases,
        "correct_abstention_rate": {"ratio": car_ratio, "percentage": car_pct},
        "false_confidence_rate": {"ratio": fcr_ratio, "percentage": fcr_pct},
        "citation_validity_l1": {"ratio": cvr_ratio, "percentage": cvr_pct},
        "avg_iterations": avg_iterations,
        "avg_latency_sec": avg_latency,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    print("\n================ SUMMARY METRICS ================")
    print(json.dumps(summary, indent=2))

    return {"summary": summary, "results": results}

def main():
    parser = argparse.ArgumentParser(description="Run Agentic SRE Robustness Benchmark")
    parser.add_argument("--suite", choices=["dev", "holdout", "both"], default="dev", help="Benchmark suite to run")
    args = parser.parse_args()

    dev_dir = BASE_DIR / "eval" / "datasets" / "dev"
    holdout_dir = BASE_DIR / "eval" / "datasets" / "holdout"

    if args.suite in ["dev", "both"]:
        dev_res = evaluate_suite(dev_dir, suite_name="Development Suite")
        out_file = BASE_DIR / "eval" / "dev_results_latest.json"
        with open(out_file, "w") as f:
            json.dump(dev_res, f, indent=2)
        print(f"\nSaved dev results to {out_file}")

    if args.suite in ["holdout", "both"]:
        holdout_res = evaluate_suite(holdout_dir, suite_name="Frozen Holdout Suite")
        out_file = BASE_DIR / "eval" / "holdout_results_latest.json"
        with open(out_file, "w") as f:
            json.dump(holdout_res, f, indent=2)
        print(f"\nSaved holdout results to {out_file}")

if __name__ == "__main__":
    main()
