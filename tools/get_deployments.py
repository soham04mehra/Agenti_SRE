import json
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR

def get_deployments(service_name: str) -> Dict[str, Any]:
    """
    Diagnostic Tool: Retrieves recent deployment and configuration history.
    Used to check if an incident correlates with a recent change.
    """
    now = datetime.utcnow()
    recent_time = (now - timedelta(minutes=15)).isoformat() + "Z"

    deploy_file = DATA_DIR / "deployments.json"
    if deploy_file.exists():
        try:
            with open(deploy_file, "r") as f:
                data = json.load(f)
                if data.get("has_bad_deployment"):
                    return {
                        "status": "success",
                        "service": service_name,
                        "citation": f"deployments/{service_name}/history",
                        "deployments": [
                            {
                                "deployment_id": f"dep_{data.get('version', 'v2.4.1')}",
                                "service": service_name,
                                "timestamp": recent_time,
                                "version": data.get("version", "v2.4.1"),
                                "deployed_by": "ci-cd-bot",
                                "changes": "Updated payment gateway endpoint configuration and DB pool timeout settings",
                                "config_diff": data.get("config_diff", {
                                    "PAYMENT_GATEWAY_URL": "http://invalid-host:9999",
                                    "DB_POOL_MAX_CONNECTIONS": 10
                                })
                            }
                        ]
                    }
                else:
                    return {
                        "status": "success",
                        "service": service_name,
                        "citation": f"deployments/{service_name}/history",
                        "deployments": [
                            {
                                "deployment_id": "dep_v1.2.3",
                                "service": service_name,
                                "timestamp": recent_time,
                                "version": "v1.2.3",
                                "deployed_by": "ci-cd-bot",
                                "changes": "Routine dependencies maintenance and security patches",
                                "config_diff": {}
                            }
                        ]
                    }
        except Exception:
            pass

    # Default fallback deployment history record for fault testing
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
