import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEV_DIR = BASE_DIR / "eval" / "datasets" / "dev"
HOLDOUT_DIR = BASE_DIR / "eval" / "datasets" / "holdout"

DEV_DIR.mkdir(parents=True, exist_ok=True)
HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)

# 18 Development Cases
DEV_CASES = [
    # 1. Clear Diagnosis (3 cases)
    {
        "case_id": "dev_001",
        "incident_description": "Checkout service degraded: persistent connection acquisition timeouts and elevated 500 error rates on payment_service.",
        "category": "clear_diagnosis",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "db_pool_exhaustion",
        "allowed_root_causes": ["db_pool_exhaustion", "database_connection_pool_exhaustion"],
        "supporting_evidence": ["DB pool exhausted: max_connections=10 reached", "db_connections_active=10"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },
    {
        "case_id": "dev_002",
        "incident_description": "Catastrophic 100% failure on all payment endpoints immediately following deployment release v2.4.1.",
        "category": "clear_diagnosis",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "bad_deployment",
        "allowed_root_causes": ["bad_deployment", "invalid_gateway_url_configuration"],
        "supporting_evidence": ["ConfigurationError: Invalid payment gateway endpoint URL", "Deployment v2.4.1 modified PAYMENT_GATEWAY_URL"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "get_deployments"],
        "difficulty": "medium",
        "degraded_expected": False
    },
    {
        "case_id": "dev_003",
        "incident_description": "Monitored memory leak: heap consumption reached 92% (1950MB/2048MB) with climbing response latency.",
        "category": "clear_diagnosis",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "memory_leak",
        "allowed_root_causes": ["memory_leak", "heap_utilization_spike"],
        "supporting_evidence": ["High memory usage detected: 92% heap utilized", "memory_usage_mb=1950.0"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },

    # 2. Insufficient Evidence (3 cases)
    {
        "case_id": "dev_004",
        "incident_description": "User reported occasional sluggish checkout experience during peak morning traffic.",
        "category": "insufficient_evidence",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "dev_005",
        "incident_description": "Customer claims payment button failed to respond on mobile device two hours ago.",
        "category": "insufficient_evidence",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "dev_006",
        "incident_description": "Minor metric jitter alert triggered on payment processing queue latency.",
        "category": "insufficient_evidence",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["query_metrics"],
        "difficulty": "hard",
        "degraded_expected": False
    },

    # 3. Noisy Evidence (3 cases)
    {
        "case_id": "dev_007",
        "incident_description": "Severe payment processing delays with DB connection acquisition errors amidst periodic cache eviction warnings and cron heartbeats.",
        "category": "noisy_evidence",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "db_pool_exhaustion",
        "allowed_root_causes": ["db_pool_exhaustion"],
        "supporting_evidence": ["DB pool exhausted: max_connections=10 reached"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "dev_008",
        "incident_description": "Payment requests throwing 100% gateway errors after v2.4.1 deployment release, along with background SSL renegotiation notices.",
        "category": "noisy_evidence",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "bad_deployment",
        "allowed_root_causes": ["bad_deployment"],
        "supporting_evidence": ["ConfigurationError: Invalid payment gateway endpoint URL", "Deployment v2.4.1 modified PAYMENT_GATEWAY_URL"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "get_deployments"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "dev_009",
        "incident_description": "Steadily climbing latency accompanied by 92% heap utilization warnings and routine thread pool resizing notices.",
        "category": "noisy_evidence",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "memory_leak",
        "allowed_root_causes": ["memory_leak"],
        "supporting_evidence": ["High memory usage detected: 92% heap utilized"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "hard",
        "degraded_expected": False
    },

    # 4. Conflicting Evidence (3 cases)
    {
        "case_id": "dev_010",
        "incident_description": "Alert flags external gateway timeout, but metric telemetry shows dependency latency is healthy at 18ms while database connections are maxed at 10.",
        "category": "conflicting_evidence",
        "affected_service": "payment_service",
        "expected_status": "unresolved_conflict",
        "expected_root_cause": "unresolved",
        "allowed_root_causes": ["unresolved", "insufficient_evidence", "db_pool_exhaustion"],
        "supporting_evidence": ["db_connections_active=10"],
        "contradicting_evidence": ["dependency_latency_ms=18.0"],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "dev_011",
        "incident_description": "Alert claims bad deployment broke payment gateway URL, but deployment history shows latest deployment was documentation changes only.",
        "category": "conflicting_evidence",
        "affected_service": "payment_service",
        "expected_status": "unresolved_conflict",
        "expected_root_cause": "unresolved",
        "allowed_root_causes": ["unresolved", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": ["config_diff contains only README update"],
        "expected_tool_sources": ["get_deployments", "fetch_logs"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "dev_012",
        "incident_description": "Alert reports critical memory exhaustion, but metrics report heap usage is only 210MB/2048MB (10%) and logs indicate client auth 401s.",
        "category": "conflicting_evidence",
        "affected_service": "payment_service",
        "expected_status": "unresolved_conflict",
        "expected_root_cause": "unresolved",
        "allowed_root_causes": ["unresolved", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": ["memory_usage_mb=210.0"],
        "expected_tool_sources": ["query_metrics", "fetch_logs"],
        "difficulty": "hard",
        "degraded_expected": False
    },

    # 5. Red Herring (3 cases)
    {
        "case_id": "dev_013",
        "incident_description": "Isolated warning: Temporary retry on benign cache query observed in payment service log.",
        "category": "red_herring",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": ["Temporary retry on benign cache query"],
        "contradicting_evidence": ["error_rate=0.01", "latency_ms=50.0"],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },
    {
        "case_id": "dev_014",
        "incident_description": "Garbage collector logging minor cycle pause of 110ms with zero impact on payment throughput.",
        "category": "red_herring",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": ["error_rate=0.0"],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },
    {
        "case_id": "dev_015",
        "incident_description": "Transient queue depth warning on non-critical analytics ping that self-resolved in 4 seconds.",
        "category": "red_herring",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": ["error_rate=0.0"],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },

    # 6. Missing Diagnostic Source (3 cases)
    {
        "case_id": "dev_016",
        "incident_description": "Payment service degraded, but metrics snapshot repository is unavailable (404 Not Found).",
        "category": "missing_diagnostic_source",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence", "db_pool_exhaustion"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["query_metrics"],
        "difficulty": "hard",
        "degraded_expected": True
    },
    {
        "case_id": "dev_017",
        "incident_description": "Customer order creation failure reported, but service log file is empty / unreadable.",
        "category": "missing_diagnostic_source",
        "affected_service": "order_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs"],
        "difficulty": "hard",
        "degraded_expected": True
    },
    {
        "case_id": "dev_018",
        "incident_description": "Sudden latency spike on payment flow, but deployment history service returns gateway timeout.",
        "category": "missing_diagnostic_source",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["get_deployments"],
        "difficulty": "hard",
        "degraded_expected": True
    }
]

# 18 Frozen Holdout Cases
HOLDOUT_CASES = [
    # 1. Clear Diagnosis (3 cases)
    {
        "case_id": "hold_001",
        "incident_description": "Critical latency spike: External payment gateway calls timing out after 30000ms with 80% error rate.",
        "category": "clear_diagnosis",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "downstream_timeout",
        "allowed_root_causes": ["downstream_timeout", "gateway_timeout", "dependency_latency"],
        "supporting_evidence": ["GatewayTimeout: Call to external payment gateway timed out after 30000ms", "dependency_latency_ms=30000.0"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },
    {
        "case_id": "hold_002",
        "incident_description": "Database connection saturation: max active connections 10 reached causing connection acquisition failure on payment processing.",
        "category": "clear_diagnosis",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "db_pool_exhaustion",
        "allowed_root_causes": ["db_pool_exhaustion", "database_connection_pool_exhaustion"],
        "supporting_evidence": ["DB pool exhausted: max_connections=10 reached", "db_connections_active=10"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },
    {
        "case_id": "hold_003",
        "incident_description": "Immediate service failure: ConfigurationError invalid payment gateway endpoint URL 'http://invalid-host:9999' post deployment.",
        "category": "clear_diagnosis",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "bad_deployment",
        "allowed_root_causes": ["bad_deployment", "invalid_gateway_url_configuration"],
        "supporting_evidence": ["ConfigurationError: Invalid payment gateway endpoint URL", "Deployment v2.4.1 modified PAYMENT_GATEWAY_URL"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "get_deployments"],
        "difficulty": "medium",
        "degraded_expected": False
    },

    # 2. Insufficient Evidence (3 cases)
    {
        "case_id": "hold_004",
        "incident_description": "Support escalation: single enterprise user report of order delay during off-peak hours.",
        "category": "insufficient_evidence",
        "affected_service": "order_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "hold_005",
        "incident_description": "Transient synthetic probe ping latency fluctuation on edge CDN node.",
        "category": "insufficient_evidence",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["query_metrics"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "hold_006",
        "incident_description": "Vague user report: checkout spinner took slightly longer than usual on mobile web.",
        "category": "insufficient_evidence",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "hard",
        "degraded_expected": False
    },

    # 3. Noisy Evidence (3 cases)
    {
        "case_id": "hold_007",
        "incident_description": "External payment gateway timed out after 30000ms amidst background DNS lookup retry logs and telemetry flush notices.",
        "category": "noisy_evidence",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "downstream_timeout",
        "allowed_root_causes": ["downstream_timeout"],
        "supporting_evidence": ["GatewayTimeout: Call to external payment gateway timed out after 30000ms"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "hold_008",
        "incident_description": "Database pool limit reached on payment service with intermittent redis cache miss notices in log stream.",
        "category": "noisy_evidence",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "db_pool_exhaustion",
        "allowed_root_causes": ["db_pool_exhaustion"],
        "supporting_evidence": ["DB pool exhausted: max_connections=10 reached"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "hold_009",
        "incident_description": "ConfigurationError invalid gateway URL after deployment v2.4.1 alongside routine Kubernetes liveness probe logs.",
        "category": "noisy_evidence",
        "affected_service": "payment_service",
        "expected_status": "resolved",
        "expected_root_cause": "bad_deployment",
        "allowed_root_causes": ["bad_deployment"],
        "supporting_evidence": ["ConfigurationError: Invalid payment gateway endpoint URL"],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs", "get_deployments"],
        "difficulty": "hard",
        "degraded_expected": False
    },

    # 4. Conflicting Evidence (3 cases)
    {
        "case_id": "hold_010",
        "incident_description": "Alert asserts database pool exhaustion, but telemetry confirms DB active connections = 2/10 and external dependency latency is 30500ms.",
        "category": "conflicting_evidence",
        "affected_service": "payment_service",
        "expected_status": "unresolved_conflict",
        "expected_root_cause": "unresolved",
        "allowed_root_causes": ["unresolved", "insufficient_evidence", "downstream_timeout"],
        "supporting_evidence": ["dependency_latency_ms=30000.0"],
        "contradicting_evidence": ["db_connections_active=2"],
        "expected_tool_sources": ["query_metrics", "fetch_logs"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "hold_011",
        "incident_description": "Alert claims recent deployment broke payment endpoint, but git commit log diff indicates only markdown documentation changes.",
        "category": "conflicting_evidence",
        "affected_service": "payment_service",
        "expected_status": "unresolved_conflict",
        "expected_root_cause": "unresolved",
        "allowed_root_causes": ["unresolved", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": ["config_diff contains only README update"],
        "expected_tool_sources": ["get_deployments"],
        "difficulty": "hard",
        "degraded_expected": False
    },
    {
        "case_id": "hold_012",
        "incident_description": "Alert signals severe heap exhaustion, but metrics indicate memory usage is at 12% and error logs show 403 Forbidden credential errors.",
        "category": "conflicting_evidence",
        "affected_service": "payment_service",
        "expected_status": "unresolved_conflict",
        "expected_root_cause": "unresolved",
        "allowed_root_causes": ["unresolved", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": ["memory_usage_mb=245.0"],
        "expected_tool_sources": ["query_metrics", "fetch_logs"],
        "difficulty": "hard",
        "degraded_expected": False
    },

    # 5. Red Herring (3 cases)
    {
        "case_id": "hold_013",
        "incident_description": "Kafka consumer group rebalance in progress warning log, duration 220ms, overall system error rate remains 0.0%.",
        "category": "red_herring",
        "affected_service": "order_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": ["error_rate=0.0"],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },
    {
        "case_id": "hold_014",
        "incident_description": "Non-critical rate limit warning on internal metrics reporting agent, payment processing unaffected.",
        "category": "red_herring",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": ["error_rate=0.0"],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },
    {
        "case_id": "hold_015",
        "incident_description": "Prometheus scraping timeout warning on replica-2, immediate retry succeeded with zero dropped requests.",
        "category": "red_herring",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": ["error_rate=0.0"],
        "expected_tool_sources": ["fetch_logs", "query_metrics"],
        "difficulty": "medium",
        "degraded_expected": False
    },

    # 6. Missing Diagnostic Source (3 cases)
    {
        "case_id": "hold_016",
        "incident_description": "Payment error rate alert triggered, but metrics monitoring agent is unreachable.",
        "category": "missing_diagnostic_source",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["query_metrics"],
        "difficulty": "hard",
        "degraded_expected": True
    },
    {
        "case_id": "hold_017",
        "incident_description": "Transaction processing failures reported, but payment service log file is empty.",
        "category": "missing_diagnostic_source",
        "affected_service": "payment_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["fetch_logs"],
        "difficulty": "hard",
        "degraded_expected": True
    },
    {
        "case_id": "hold_018",
        "incident_description": "Order creation latency climbing, but deployment commit history is unavailable.",
        "category": "missing_diagnostic_source",
        "affected_service": "order_service",
        "expected_status": "insufficient_evidence",
        "expected_root_cause": "none",
        "allowed_root_causes": ["none", "insufficient_evidence"],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "expected_tool_sources": ["get_deployments"],
        "difficulty": "hard",
        "degraded_expected": True
    }
]

def main():
    print(f"Generating 18 Development Cases in {DEV_DIR}...")
    for case in DEV_CASES:
        file_path = DEV_DIR / f"{case['case_id']}.json"
        with open(file_path, "w") as f:
            json.dump(case, f, indent=2)

    print(f"Generating 18 Holdout Cases in {HOLDOUT_DIR}...")
    for case in HOLDOUT_CASES:
        file_path = HOLDOUT_DIR / f"{case['case_id']}.json"
        with open(file_path, "w") as f:
            json.dump(case, f, indent=2)

    print(f"✅ Generated {len(DEV_CASES)} Dev cases and {len(HOLDOUT_CASES)} Holdout cases.")

if __name__ == "__main__":
    main()
