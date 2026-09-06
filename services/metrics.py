import json
from datetime import datetime
from config import METRICS_DIR

class MetricsTracker:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.metrics_file = METRICS_DIR / f"{service_name}.json"
        
        # Default baseline healthy metrics
        self.metrics = {
            "service": self.service_name,
            "error_rate": 0.0,
            "latency_ms": 45.0,
            "db_connections_active": 3,
            "memory_usage_mb": 256.0,
            "dependency_latency_ms": 20.0,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        self.save()

    def update(self, **kwargs):
        """Update metric values and save to file."""
        self.metrics.update(kwargs)
        self.metrics["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self.save()

    def save(self):
        """Write current metrics to JSON file."""
        with open(self.metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)

    def get_metrics(self) -> dict:
        """Read metrics from file."""
        if self.metrics_file.exists():
            with open(self.metrics_file, "r") as f:
                return json.load(f)
        return self.metrics
