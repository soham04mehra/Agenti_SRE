import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import GROUND_TRUTHS_DIR
from services.order_service import OrderService

# Ground truth definitions for the 5 fault scenarios
FAULT_GROUND_TRUTH = {
    "db_pool_exhaustion": {
        "affected_service": "payment_service",
        "symptom": "High error rate and database connection timeouts during payment processing",
        "expected_evidence": ["DB pool exhausted", "max_connections=10 reached", "db_connections_active=10"],
        "expected_root_cause": "Database connection pool exhaustion in payment_service due to max active connections reached.",
        "expected_action": "Increase database connection pool limit or release idle connections."
    },
    "bad_deployment": {
        "affected_service": "payment_service",
        "symptom": "Immediate 100% error rate on payment processing after deployment",
        "expected_evidence": ["ConfigurationError", "Invalid payment gateway endpoint URL", "error_rate=1.0"],
        "expected_root_cause": "Bad deployment configuration typo pointing payment_service to invalid gateway endpoint URL.",
        "expected_action": "Rollback deployment or fix gateway URL configuration environment variable."
    },
    "memory_leak": {
        "affected_service": "payment_service",
        "symptom": "Steadily rising latency and memory warning logs",
        "expected_evidence": ["High memory usage detected", "92% heap utilized", "memory_usage_mb=1950.0"],
        "expected_root_cause": "Memory leak in payment_service causing heap utilization to reach 92%.",
        "expected_action": "Inspect heap dump, fix uncollected payment session objects, and restart payment_service."
    },
    "downstream_timeout": {
        "affected_service": "payment_service",
        "symptom": "Extreme latency spikes (30s) and gateway timeout errors",
        "expected_evidence": ["GatewayTimeout", "timed out after 30000ms", "dependency_latency_ms=30000.0"],
        "expected_root_cause": "Downstream external payment gateway latency timeout.",
        "expected_action": "Verify downstream payment gateway status and configure circuit breaker pattern."
    },
    "red_herring": {
        "affected_service": "payment_service",
        "symptom": "Isolated benign cache warning log with healthy overall system metrics",
        "expected_evidence": ["Temporary retry on benign cache query", "healthy error_rate and latency"],
        "expected_root_cause": "No systemic fault detected. Transient benign warning log.",
        "expected_action": "No remediation required. Monitor service."
    }
}

class FaultInjector:
    def __init__(self):
        self.order_service = OrderService()

    def inject_fault(self, fault_type: str, request_count: int = 5) -> str:
        """Inject a fault, simulate traffic, and save ground truth JSON."""
        print(f"⚡ Injecting fault: '{fault_type}'...")
        
        self.order_service.set_fault_mode(fault_type)
        
        # Simulate traffic through microservices
        for i in range(request_count):
            self.order_service.create_order(
                user_id=f"usr_{i+100}",
                item_id=f"item_{i+1}",
                amount=50.0 + (i * 10)
            )
            time.sleep(0.1)

        # Reset fault mode
        self.order_service.set_fault_mode(None)

        # Save Ground Truth JSON record if valid fault type
        if fault_type in FAULT_GROUND_TRUTH:
            incident_id = f"inc_{int(time.time())}"
            gt_data = {
                "incident_id": incident_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "fault_type": fault_type,
                **FAULT_GROUND_TRUTH[fault_type]
            }
            
            gt_file = GROUND_TRUTHS_DIR / f"{incident_id}.json"
            with open(gt_file, "w") as f:
                json.dump(gt_data, f, indent=2)

            print(f"✅ Telemetry generated in data/logs & data/metrics!")
            print(f"📄 Ground truth created at: {gt_file}")
            return incident_id
        
        print("✅ Traffic simulation finished (no fault mode).")
        return ""

if __name__ == "__main__":
    injector = FaultInjector()
    
    # Check if fault_type argument provided
    fault = sys.argv[1] if len(sys.argv) > 1 else "db_pool_exhaustion"
    injector.inject_fault(fault_type=fault)
