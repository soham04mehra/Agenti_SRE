from datetime import datetime, timedelta
from typing import Dict, Any

def get_deployments(service_name: str) -> Dict[str, Any]:
    """
    Diagnostic Tool: Retrieves recent deployment and configuration history.
    Used to check if an incident correlates with a recent change.
    """
    now = datetime.utcnow()
    recent_time = (now - timedelta(minutes=15)).isoformat() + "Z"

    # Simulated deployment history record for fault testing
    deployments = [
        {
            "deployment_id": "dep_v2.4.1",
            "service": service_name,
            "timestamp": recent_time,
            "version": "v2.4.1",
            "deployed_by": "ci-cd-bot",
            "changes": "Updated payment gateway endpoint configuration and DB pool timeout settings",
            "config_diff": {
                "PAYMENT_GATEWAY_URL": "http://invalid-host:9999",
                "DB_POOL_MAX_CONNECTIONS": 10
            }
        }
    ]

    return {
        "status": "success",
        "service": service_name,
        "citation": f"deployments/{service_name}/history",
        "deployments": deployments
    }
