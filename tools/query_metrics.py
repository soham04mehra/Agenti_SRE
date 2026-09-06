import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import METRICS_DIR

def query_metrics(service_name: str) -> dict:
    """
    Diagnostic Tool: Reads metrics snapshot for a service.
    Returns error rates, latencies, DB active connections, and memory usage.
    """
    metrics_file = METRICS_DIR / f"{service_name}.json"

    if not metrics_file.exists():
        return {
            "status": "not_found",
            "message": f"Metrics snapshot for '{service_name}' not found at {metrics_file}",
            "metrics": {}
        }

    with open(metrics_file, "r") as f:
        metrics_data = json.load(f)

    return {
        "status": "success",
        "service": service_name,
        "citation": str(metrics_file),
        "metrics": metrics_data
    }
