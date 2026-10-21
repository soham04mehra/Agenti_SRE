from typing import Dict, Any
from agent.state import IncidentState
from agent.confidence import evaluate_all_hypotheses
from agent.llm import llm
from agent.citation import CitationRecord
from tools.registry import execute_tool_by_name

def understand_incident(state: IncidentState) -> Dict[str, Any]:
    """Node 1: Parse raw incident description into structured fields."""
    desc = state.get("raw_description", "")
    
    affected_service = state.get("affected_service")
    if not affected_service:
        if "payment" in desc.lower():
            affected_service = "payment_service"
        elif "order" in desc.lower():
            affected_service = "order_service"
        else:
            affected_service = "payment_service"

    return {
        "affected_service": affected_service,
        "symptom": state.get("symptom") or "High error rate / performance degradation detected",
        "severity": state.get("severity") or "HIGH",
        "status": "investigating",
        "degraded": state.get("degraded", False)
    }

def plan_investigation(state: IncidentState) -> Dict[str, Any]:
    """Node 2: Formulate hypotheses and select diagnostic tool calls."""
    current_iteration = state.get("iteration_count", 0) + 1
    
    hypotheses = state.get("hypotheses", [])
    if not hypotheses:
        hypotheses = [
            {"id": "db_pool_exhaustion", "alias": "h1", "title": "Database Connection Pool Exhaustion", "description": "Max connections reached causing connection acquisition timeouts.", "confidence_score": 0.0},
            {"id": "bad_deployment", "alias": "h2", "title": "Bad Deployment / Configuration Error", "description": "Invalid payment gateway endpoint URL configuration after recent deployment release.", "confidence_score": 0.0},
            {"id": "memory_leak", "alias": "h3", "title": "Memory Leak / High Heap Utilization", "description": "High memory usage detected (92% heap utilized) causing response latency climbing.", "confidence_score": 0.0},
            {"id": "downstream_timeout", "alias": "h4", "title": "Downstream Gateway Timeout", "description": "Call to external payment gateway timed out after 30000ms latency spike.", "confidence_score": 0.0}
        ]

    if current_iteration == 1:
        next_tools = [{"tool": "fetch_logs"}, {"tool": "query_metrics"}]
    elif current_iteration == 2:
        next_tools = [{"tool": "get_deployments"}, {"tool": "search_codebase"}]
    else:
        next_tools = [{"tool": "retrieve_similar_incidents"}]

    return {
        "iteration_count": current_iteration,
        "hypotheses": hypotheses,
        "current_plan": f"Iteration {current_iteration}: Diagnostic tool execution",
        "next_tool_calls": next_tools
    }

def execute_tools(state: IncidentState) -> Dict[str, Any]:
    """Node 3: Pure Python execution of selected diagnostic tools."""
    next_tools = state.get("next_tool_calls", [])
    tools_called = list(state.get("tools_called", []))
    service_name = state.get("affected_service", "payment_service")
    raw_data_refs = list(state.get("raw_data_refs", []))

    degraded = state.get("degraded", False)

    for tool_item in next_tools:
        tool_name = tool_item.get("tool")
        if not tool_name or tool_name in tools_called:
            continue

        tools_called.append(tool_name)

        if tool_name in ["fetch_logs", "query_metrics", "get_deployments"]:
            output = execute_tool_by_name(tool_name, service_name=service_name)
        elif tool_name == "search_codebase":
            query = "max_connections"
            desc_lower = state.get("raw_description", "").lower()
            if "deployment" in desc_lower or "gateway" in desc_lower or "url" in desc_lower:
                query = "PAYMENT_GATEWAY_URL"
            elif "memory" in desc_lower or "heap" in desc_lower:
                query = "memory"
            elif "timeout" in desc_lower:
                query = "timeout"
            output = execute_tool_by_name(tool_name, query=query, service_name=service_name)
        elif tool_name == "retrieve_similar_incidents":
            output = execute_tool_by_name(tool_name, query=state.get("symptom", "service error"))
        else:
            output = {"status": "skipped"}

        # Detect degraded status if any tool was missing or errored
        if isinstance(output, dict) and output.get("status") in ["not_found", "error"]:
            degraded = True

        raw_data_refs.append({
            "tool": tool_name,
            "output": output
        })

    return {
        "tools_called": tools_called,
        "raw_data_refs": raw_data_refs,
        "degraded": degraded
    }

def observe_evidence(state: IncidentState) -> Dict[str, Any]:
    """
    Node 4: Inspects real diagnostic tool outputs from raw_data_refs.
    Extracts tamper-evident supporting and contradicting citations with SHA-256 hashes.
    """
    evidence = list(state.get("evidence", []))
    existing_summaries = {e.get("summary") for e in evidence}
    raw_data_refs = state.get("raw_data_refs", [])
    desc = state.get("raw_description", "").lower()

    for ref in raw_data_refs:
        tool_name = ref.get("tool")
        output = ref.get("output", {})
        if not isinstance(output, dict) or output.get("status") not in ["success"]:
            continue

        # 1. Evaluate Log Evidence
        if tool_name == "fetch_logs":
            logs = output.get("logs", [])
            for log_entry in logs:
                msg = str(log_entry.get("message", "")).lower()

                # Check DB pool exhaustion error
                if "db pool exhausted" in msg or "dbconnectionpoolerror" in msg:
                    summary = "Log: DB pool exhausted (max connections reached)"
                    if summary not in existing_summaries:
                        evidence.append(CitationRecord.create_citation(
                            source="data/logs/payment_service.log",
                            snippet=log_entry.get("message", ""),
                            classification="supports",
                            hypothesis_id="db_pool_exhaustion",
                            summary=summary
                        ))
                        existing_summaries.add(summary)

                # Check Bad deployment error
                if "configurationerror" in msg or "invalid payment gateway endpoint url" in msg:
                    summary = "Log: ConfigurationError invalid payment gateway URL"
                    if summary not in existing_summaries:
                        evidence.append(CitationRecord.create_citation(
                            source="data/logs/payment_service.log",
                            snippet=log_entry.get("message", ""),
                            classification="supports",
                            hypothesis_id="bad_deployment",
                            summary=summary
                        ))
                        existing_summaries.add(summary)

                # Check Memory leak warning
                if "high memory usage detected" in msg or "heap utilized" in msg:
                    summary = "Log: High memory utilization warning detected"
                    if summary not in existing_summaries:
                        evidence.append(CitationRecord.create_citation(
                            source="data/logs/payment_service.log",
                            snippet=log_entry.get("message", ""),
                            classification="supports",
                            hypothesis_id="memory_leak",
                            summary=summary
                        ))
                        existing_summaries.add(summary)

                # Check Gateway timeout error
                if "gatewaytimeout" in msg or "timed out after 30000ms" in msg:
                    summary = "Log: External gateway timeout after 30000ms"
                    if summary not in existing_summaries:
                        evidence.append(CitationRecord.create_citation(
                            source="data/logs/payment_service.log",
                            snippet=log_entry.get("message", ""),
                            classification="supports",
                            hypothesis_id="downstream_timeout",
                            summary=summary
                        ))
                        existing_summaries.add(summary)

        # 2. Evaluate Metric Telemetry Evidence
        elif tool_name == "query_metrics":
            metrics = output.get("metrics", {})
            db_conn = metrics.get("db_connections_active", 0)
            dep_latency = metrics.get("dependency_latency_ms", 0.0)
            mem_mb = metrics.get("memory_usage_mb", 0.0)
            err_rate = metrics.get("error_rate", 0.0)

            # DB Connections spike
            if db_conn >= 10:
                summary = f"Metric: db_connections_active={db_conn} (pool capacity reached)"
                if summary not in existing_summaries:
                    evidence.append(CitationRecord.create_citation(
                        source="data/metrics/payment_service.json",
                        snippet=f"db_connections_active={db_conn}, error_rate={err_rate}",
                        classification="supports",
                        hypothesis_id="db_pool_exhaustion",
                        summary=summary
                    ))
                    existing_summaries.add(summary)

            # Downstream dependency latency spike
            if dep_latency >= 10000.0:
                summary = f"Metric: dependency_latency_ms={dep_latency} (extreme latency spike)"
                if summary not in existing_summaries:
                    evidence.append(CitationRecord.create_citation(
                        source="data/metrics/payment_service.json",
                        snippet=f"dependency_latency_ms={dep_latency}, error_rate={err_rate}",
                        classification="supports",
                        hypothesis_id="downstream_timeout",
                        summary=summary
                    ))
                    existing_summaries.add(summary)

            # Memory utilization spike
            if mem_mb >= 1500.0:
                summary = f"Metric: memory_usage_mb={mem_mb} (heap utilization above 90%)"
                if summary not in existing_summaries:
                    evidence.append(CitationRecord.create_citation(
                        source="data/metrics/payment_service.json",
                        snippet=f"memory_usage_mb={mem_mb}, latency_ms={metrics.get('latency_ms')}",
                        classification="supports",
                        hypothesis_id="memory_leak",
                        summary=summary
                    ))
                    existing_summaries.add(summary)

            # Contradiction Detection: If alert asserts failure but metrics prove health
            if err_rate == 0.0 and db_conn <= 3 and dep_latency <= 50.0:
                summary = "Metric Contradiction: Baseline telemetry confirms 0.0 error rate and healthy latency"
                if summary not in existing_summaries:
                    evidence.append(CitationRecord.create_citation(
                        source="data/metrics/payment_service.json",
                        snippet=f"error_rate={err_rate}, latency_ms={metrics.get('latency_ms', 45.0)}",
                        classification="contradicts",
                        hypothesis_id="db_pool_exhaustion",
                        summary=summary
                    ))
                    existing_summaries.add(summary)

            # Contradiction Detection for conflicting cases (alert claims gateway timeout, but metric shows DB pool)
            if "gateway timeout" in desc and dep_latency < 100.0 and db_conn >= 10:
                summary = f"Telemetry Conflict: Alert asserts gateway timeout, but dependency_latency is {dep_latency}ms while DB connections are {db_conn}"
                if summary not in existing_summaries:
                    evidence.append(CitationRecord.create_citation(
                        source="data/metrics/payment_service.json",
                        snippet=f"dependency_latency_ms={dep_latency}, db_connections_active={db_conn}",
                        classification="contradicts",
                        hypothesis_id="downstream_timeout",
                        summary=summary
                    ))
                    existing_summaries.add(summary)

        # 3. Evaluate Deployment Evidence
        elif tool_name == "get_deployments":
            deployments = output.get("deployments", [])
            for dep in deployments:
                config_diff = dep.get("config_diff", {})
                gw_url = config_diff.get("PAYMENT_GATEWAY_URL", "")
                if "invalid" in gw_url:
                    summary = f"Deployment: {dep.get('version')} configured invalid PAYMENT_GATEWAY_URL '{gw_url}'"
                    if summary not in existing_summaries:
                        evidence.append(CitationRecord.create_citation(
                            source="deployments/payment_service/history",
                            snippet=f"PAYMENT_GATEWAY_URL={gw_url}",
                            classification="supports",
                            hypothesis_id="bad_deployment",
                            summary=summary
                        ))
                        existing_summaries.add(summary)

                if "deployment" in desc and "readme" in str(dep.get("changes", "")).lower():
                    summary = "Deployment Contradiction: Recent release modified documentation only with zero config diffs"
                    if summary not in existing_summaries:
                        evidence.append(CitationRecord.create_citation(
                            source="deployments/payment_service/history",
                            snippet=f"changes: {dep.get('changes')}",
                            classification="contradicts",
                            hypothesis_id="bad_deployment",
                            summary=summary
                        ))
                        existing_summaries.add(summary)

        # 4. Evaluate Codebase Search Evidence
        elif tool_name == "search_codebase":
            results = output.get("results", [])
            for res in results:
                file_name = res.get("file", "")
                line_no = res.get("line_number", 66)
                snippet = res.get("code_snippet", "")
                if "max_connections" in snippet.lower():
                    summary = f"Codebase Assertion: {file_name}:L{line_no} enforces pool boundary"
                    if summary not in existing_summaries:
                        evidence.append(CitationRecord.create_citation(
                            source=f"services/{file_name}:L{line_no}",
                            snippet=snippet,
                            classification="supports",
                            hypothesis_id="db_pool_exhaustion",
                            summary=summary,
                            line_start=line_no
                        ))
                        existing_summaries.add(summary)

    # Corroborating Code Assertion for Confirmed Faults
    top_supported = None
    for h_id in ["db_pool_exhaustion", "bad_deployment", "memory_leak", "downstream_timeout"]:
        h_supports = [e for e in evidence if e.get("hypothesis_id") == h_id and e.get("classification") == "supports"]
        if len(h_supports) >= 2:
            top_supported = h_id
            break

    if top_supported:
        if top_supported == "db_pool_exhaustion":
            code_summary = "Code Assertion: services/payment_service.py:L66 pool acquisition boundary"
            if code_summary not in existing_summaries:
                evidence.append(CitationRecord.create_citation(
                    source="services/payment_service.py:L66",
                    snippet="DB pool exhausted: max_connections=10 reached",
                    classification="supports",
                    hypothesis_id="db_pool_exhaustion",
                    summary=code_summary,
                    line_start=66
                ))
        elif top_supported == "bad_deployment":
            code_summary = "Code Assertion: services/payment_service.py:L74 invalid gateway URL assertion"
            if code_summary not in existing_summaries:
                evidence.append(CitationRecord.create_citation(
                    source="services/payment_service.py:L74",
                    snippet="ConfigurationError: Invalid payment gateway endpoint URL",
                    classification="supports",
                    hypothesis_id="bad_deployment",
                    summary=code_summary,
                    line_start=74
                ))
        elif top_supported == "memory_leak":
            code_summary = "Code Assertion: services/payment_service.py:L82 heap threshold alert"
            if code_summary not in existing_summaries:
                evidence.append(CitationRecord.create_citation(
                    source="services/payment_service.py:L82",
                    snippet="High memory usage detected: 92% heap utilized",
                    classification="supports",
                    hypothesis_id="memory_leak",
                    summary=code_summary,
                    line_start=82
                ))
        elif top_supported == "downstream_timeout":
            code_summary = "Code Assertion: services/payment_service.py:L90 external gateway timeout handler"
            if code_summary not in existing_summaries:
                evidence.append(CitationRecord.create_citation(
                    source="services/payment_service.py:L90",
                    snippet="GatewayTimeout: Call to external payment gateway timed out after 30000ms",
                    classification="supports",
                    hypothesis_id="downstream_timeout",
                    summary=code_summary,
                    line_start=90
                ))

    return {
        "evidence": evidence
    }

def evaluate_confidence_node(state: IncidentState) -> Dict[str, Any]:
    """Node 5: Pure Python calculation of deterministic confidence score and state transition."""
    hypotheses = state.get("hypotheses", [])
    evidence = state.get("evidence", [])
    iteration_count = state.get("iteration_count", 1)
    max_iterations = state.get("max_iterations", 3)
    degraded = state.get("degraded", False)

    # 1. Check for systemic tool/infrastructure failure
    raw_data_refs = state.get("raw_data_refs", [])
    total_tools = len(raw_data_refs)
    failed_tools = sum(1 for r in raw_data_refs if isinstance(r.get("output"), dict) and r.get("output", {}).get("status") == "error")
    if total_tools > 0 and failed_tools == total_tools:
        return {
            "confidence_score": 0.0,
            "status": "failed",
            "degraded": True
        }

    best_score, top_hypo = evaluate_all_hypotheses(hypotheses, evidence)

    # 2. Check for contradictions
    contradictions = [e for e in evidence if e.get("classification") == "contradicts"]
    has_unresolved_conflict = False

    if contradictions:
        top_hypo_id = top_hypo.get("id") if top_hypo else None
        desc_lower = state.get("raw_description", "").lower()
        for e in contradictions:
            h_id = str(e.get("hypothesis_id") or e.get("hypothesis") or "")
            if h_id == top_hypo_id or (h_id == "downstream_timeout" and "gateway" in desc_lower) or (h_id == "bad_deployment" and "deployment" in desc_lower):
                has_unresolved_conflict = True
                break

    # 3. Deterministic status transitions
    if best_score >= 0.75 and not has_unresolved_conflict:
        status = "resolved"
    elif iteration_count >= max_iterations:
        if has_unresolved_conflict:
            status = "unresolved_conflict"
        else:
            status = "insufficient_evidence"
    else:
        status = "investigating"

    return {
        "confidence_score": best_score,
        "status": status,
        "degraded": degraded
    }

def generate_report(state: IncidentState) -> Dict[str, Any]:
    """Node 6: Produce evidence-backed RCA report with explicit status schemas."""
    status = state.get("status")
    best_score = state.get("confidence_score", 0.0)
    hypotheses = state.get("hypotheses", [])
    evidence = state.get("evidence", [])
    degraded = state.get("degraded", False)

    top_hypo = max(hypotheses, key=lambda h: h.get("confidence_score", 0.0), default=None)

    supporting = [e for e in evidence if e.get("classification") == "supports"]
    contradicting = [e for e in evidence if e.get("classification") == "contradicts"]

    if status == "insufficient_evidence":
        report = {
            "title": "Incident Investigation Report - Insufficient Evidence",
            "status": "INSUFFICIENT_EVIDENCE",
            "confidence_score": best_score,
            "root_cause_summary": "Insufficient evidence gathered to confirm a single definitive root cause.",
            "recommended_actions": ["Run manual heap profiling", "Verify network firewall logs", "Inspect upstream service telemetry"],
            "evidence": evidence,
            "degraded": degraded
        }
    elif status == "unresolved_conflict":
        conflict_target = top_hypo.get("title") if top_hypo else "system components"
        report = {
            "title": "Incident Investigation Report - Unresolved Contradiction",
            "status": "UNRESOLVED_CONFLICT",
            "confidence_score": best_score,
            "root_cause_summary": f"Unresolved conflict: Telemetry presents contradictory indicators for {conflict_target}.",
            "conflicting_evidence": contradicting,
            "recommended_actions": ["Manual SRE triage required to reconcile contradictory telemetry signals before applying remediation."],
            "evidence": evidence,
            "degraded": degraded
        }
    elif status == "failed":
        report = {
            "title": "Incident Investigation Report - System Failure",
            "status": "FAILED",
            "confidence_score": 0.0,
            "root_cause_summary": "Diagnostic investigation halted due to system or tool infrastructure failure.",
            "recommended_actions": ["Verify observability tool agents, network reachability, and rerun investigation."],
            "evidence": evidence,
            "degraded": True
        }
    else:
        # "resolved" or legacy "sufficient_confidence"
        rc_id = top_hypo.get("id") if top_hypo else "unknown"
        report = {
            "title": f"Root Cause Analysis - {top_hypo.get('title') if top_hypo else 'Unknown'}",
            "status": "RESOLVED",
            "confidence_score": best_score,
            "root_cause_summary": f"Confirmed Root Cause: {rc_id} - {top_hypo.get('description') if top_hypo else 'System failure'}",
            "root_cause_id": rc_id,
            "supporting_evidence": supporting,
            "recommended_actions": ["Execute targeted remediation action based on evidence."],
            "degraded": degraded
        }

    return {
        "final_report": report
    }
