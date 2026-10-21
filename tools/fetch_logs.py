import json
from pathlib import Path
import sys

# Add project root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import LOGS_DIR

def fetch_logs(service_name: str, level_filter: str = "ERROR", limit: int = 10) -> dict:
    """
    Diagnostic Tool: Reads structured JSON log entries for a service.
    Returns matching log entries and a summary reference.
    """
    log_file = LOGS_DIR / f"{service_name}.log"
    
    if not log_file.exists():
        return {
            "status": "not_found",
            "message": f"Log file for service '{service_name}' not found at {log_file}",
            "logs": []
        }

    matching_logs = []
    
    with open(log_file, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if level_filter:
                    filter_set = {"ERROR", "WARNING", "WARN"} if level_filter.upper() in ["ERROR", "WARN", "WARNING"] else {level_filter.upper()}
                    if entry.get("level") not in filter_set:
                        continue
                matching_logs.append(entry)
            except json.JSONDecodeError:
                continue

    # Get recent logs up to limit
    recent_logs = matching_logs[-limit:]

    return {
        "status": "success",
        "service": service_name,
        "citation": str(log_file),
        "total_matched": len(matching_logs),
        "logs": recent_logs
    }
