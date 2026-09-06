from services.logger import StructuredLogger
from services.metrics import MetricsTracker
from services.payment_service import PaymentService

class OrderService:
    def __init__(self, payment_service: PaymentService = None):
        self.logger = StructuredLogger("order_service")
        self.metrics_tracker = MetricsTracker("order_service")
        self.payment_service = payment_service or PaymentService()
        self.fault_mode = None

    def set_fault_mode(self, fault_type: str | None):
        """Pass fault mode to order service and downstream payment service."""
        self.fault_mode = fault_type
        self.logger.warning("Order service fault mode updated", extra={"fault_mode": fault_type})
        self.payment_service.set_fault_mode(fault_type)
        self._apply_fault_metrics()

    def _apply_fault_metrics(self):
        """Sync order metrics with current fault mode."""
        if self.fault_mode in ["db_pool_exhaustion", "bad_deployment", "downstream_timeout"]:
            self.metrics_tracker.update(error_rate=0.90, latency_ms=1000.0)
        elif self.fault_mode == "memory_leak":
            self.metrics_tracker.update(memory_usage_mb=1800.0, latency_ms=600.0)
        else:
            self.metrics_tracker.update(error_rate=0.0, latency_ms=35.0, memory_usage_mb=200.0)

    def create_order(self, user_id: str, item_id: str, amount: float) -> dict:
        """Create an order and process payment."""
        self.logger.info("Received order creation request", extra={"user_id": user_id, "item_id": item_id, "amount": amount})

        # Process payment via payment service
        payment_result = self.payment_service.process_payment(user_id=user_id, amount=amount)

        if not payment_result.get("success"):
            self.logger.error(
                "Order creation failed due to payment error",
                extra={"user_id": user_id, "item_id": item_id, "error": payment_result.get("error")}
            )
            return {"success": False, "error": f"Order failed: {payment_result.get('error')}"}

        order_id = f"ORD-{user_id[:4]}-{item_id}"
        self.logger.info("Order created successfully", extra={"order_id": order_id, "user_id": user_id})
        
        return {
            "success": True,
            "order_id": order_id,
            "user_id": user_id,
            "item_id": item_id,
            "amount": amount
        }
