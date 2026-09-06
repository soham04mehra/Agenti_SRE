import json
from datetime import datetime, timezone
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import GROUND_TRUTHS_DIR

FAULT_TEMPLATES = [
    {
        "fault_type": "db_pool_exhaustion",
        "service": "payment_service",
        "description_template": "Payment service experiencing high error rate and database connection acquisition timeout under load",
        "expected_evidence": ["DB pool exhausted", "max_connections=10 reached", "db_connections_active=10"],
        "expected_root_cause": "Database connection pool exhaustion in payment_service due to max active connections reached.",
        "expected_action": "Increase database connection pool limit or release idle connections."
    },
    {
        "fault_type": "bad_deployment",
        "service": "payment_service",
        "description_template": "Immediate 100% error rate on payment requests following recent deployment release v2.4.1",
        "expected_evidence": ["ConfigurationError", "Invalid payment gateway endpoint URL", "error_rate=1.0"],
        "expected_root_cause": "Bad deployment configuration typo pointing payment_service to invalid gateway endpoint URL.",
        "expected_action": "Rollback deployment or fix gateway URL configuration environment variable."
    },
    {
        "fault_type": "memory_leak",
        "service": "payment_service",
        "description_template": "Gradually climbing response latency and high heap memory usage alerts on payment_service",
        "expected_evidence": ["High memory usage detected", "92% heap utilized", "memory_usage_mb=1950.0"],
        "expected_root_cause": "Memory leak in payment_service causing heap utilization to reach 92%.",
        "expected_action": "Inspect heap dump, fix uncollected payment session objects, and restart payment_service."
    },
    {
        "fault_type": "downstream_timeout",
        "service": "payment_service",
        "description_template": "Extreme latency spikes (30s) and gateway timeout errors when processing transactions",
        "expected_evidence": ["GatewayTimeout", "timed out after 30000ms", "dependency_latency_ms=30000.0"],
        "expected_root_cause": "Downstream external payment gateway latency timeout.",
        "expected_action": "Verify downstream payment gateway status and configure circuit breaker pattern."
    }
]

def generate_ground_truth_dataset(count_per_fault: int = 6) -> int:
    """Generates 24 ground truth incident scenario files."""
    GROUND_TRUTHS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clean old files
    for old_file in GROUND_TRUTHS_DIR.glob("eval_inc_*.json"):
        old_file.unlink()

    total_generated = 0

    for idx, tmpl in enumerate(FAULT_TEMPLATES):
        for i in range(count_per_fault):
            inc_id = f"eval_inc_{(idx * count_per_fault) + i + 1:03d}"
            
            data = {
                "incident_id": inc_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_description": f"{tmpl['description_template']} (Scenario #{i+1})",
                "affected_service": tmpl["service"],
                "fault_type": tmpl["fault_type"],
                "expected_evidence": tmpl["expected_evidence"],
                "expected_root_cause": tmpl["expected_root_cause"],
                "expected_action": tmpl["expected_action"],
                "is_red_herring": False
            }

            file_path = GROUND_TRUTHS_DIR / f"{inc_id}.json"
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            
            total_generated += 1

    print(f"✅ Generated {total_generated} ground-truth incident scenarios in '{GROUND_TRUTHS_DIR}'")
    return total_generated

if __name__ == "__main__":
    generate_ground_truth_dataset()
