import time
from services.logger import StructuredLogger
from services.metrics import MetricsTracker

class PaymentService:
    def __init__(self):
        self.logger = StructuredLogger("payment_service")
        self.metrics_tracker = MetricsTracker("payment_service")
        self.fault_mode = None

    def set_fault_mode(self, fault_type: str | None):
        """Enable or disable a fault injection mode."""
        self.fault_mode = fault_type
        self.logger.warning("Fault mode updated", extra={"fault_mode": fault_type})
        self._apply_fault_metrics()

    def _apply_fault_metrics(self):
        """Update metrics according to active fault type."""
        if self.fault_mode == "db_pool_exhaustion":
            self.metrics_tracker.update(
                db_connections_active=10,
                error_rate=0.95,
                latency_ms=5000.0,
                memory_usage_mb=256.0,
                dependency_latency_ms=20.0
            )
        elif self.fault_mode == "bad_deployment":
            self.metrics_tracker.update(
                error_rate=1.0,
                latency_ms=120.0,
                db_connections_active=3,
                memory_usage_mb=256.0,
                dependency_latency_ms=20.0
            )
        elif self.fault_mode == "memory_leak":
            self.metrics_tracker.update(
                memory_usage_mb=1950.0,
                latency_ms=850.0,
                db_connections_active=3,
                error_rate=0.05,
                dependency_latency_ms=20.0
            )
        elif self.fault_mode == "downstream_timeout":
            self.metrics_tracker.update(
                dependency_latency_ms=30000.0,
                latency_ms=30500.0,
                error_rate=0.80,
                db_connections_active=3,
                memory_usage_mb=256.0
            )
        elif self.fault_mode == "red_herring":
            # Normal healthy metrics, just a minor log warning
            self.metrics_tracker.update(
                error_rate=0.01,
                latency_ms=50.0,
                db_connections_active=3,
                memory_usage_mb=260.0
            )
        else:
            # Reset to baseline healthy metrics
            self.metrics_tracker.update(
                error_rate=0.0,
                latency_ms=45.0,
                db_connections_active=3,
                memory_usage_mb=256.0,
                dependency_latency_ms=20.0
            )

    def process_payment(self, user_id: str, amount: float) -> dict:
        """Process a payment request and emit logs/metrics."""
        self.logger.info("Processing payment", extra={"user_id": user_id, "amount": amount})

        # Scenario 1: DB Pool Exhaustion
        if self.fault_mode == "db_pool_exhaustion":
            self.logger.error(
                "DB pool exhausted: max_connections=10 reached, connection acquisition timed out",
                extra={"user_id": user_id, "error": "DBConnectionPoolError"}
            )
            return {"success": False, "error": "DB pool exhausted"}

        # Scenario 2: Bad Deployment / Config Typo
        if self.fault_mode == "bad_deployment":
            self.logger.error(
                "ConfigurationError: Invalid payment gateway endpoint URL 'http://invalid-host:9999'",
                extra={"user_id": user_id, "error": "ConfigurationError"}
            )
            return {"success": False, "error": "Invalid gateway config"}

        # Scenario 3: Memory Leak
        if self.fault_mode == "memory_leak":
            self.logger.warning(
                "High memory usage detected: 92% heap utilized (1950MB / 2048MB)",
                extra={"memory_usage_mb": 1950.0}
            )
            return {"success": True, "warning": "High memory usage"}

        # Scenario 4: Downstream Dependency Timeout
        if self.fault_mode == "downstream_timeout":
            self.logger.error(
                "GatewayTimeout: Call to external payment gateway timed out after 30000ms",
                extra={"user_id": user_id, "timeout_ms": 30000}
            )
            return {"success": False, "error": "Gateway timeout"}

        # Scenario 5: Red Herring (Benign Warning)
        if self.fault_mode == "red_herring":
            self.logger.warning(
                "Temporary retry on benign cache query",
                extra={"user_id": user_id}
            )
            return {"success": True, "transaction_id": f"TXN-{user_id}"}

        # Normal Healthy Execution
        self.logger.info("Payment processed successfully", extra={"user_id": user_id, "amount": amount})
        return {"success": True, "transaction_id": f"TXN-{user_id}"}
