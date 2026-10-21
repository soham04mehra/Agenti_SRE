# FAILURE_ANALYSIS.md — Failure Mode Analysis & Architectural Remediation

This document provides a post-audit analysis of system weaknesses, failure modes, telemetry bugs, and shortcut mechanisms identified during the audit of the Agentic SRE Platform, alongside the architectural remediations implemented.

---

## 1. Node 4 Substring Shortcut & Tool Output Bypass

### Symptom & Discovery
During the Phase 1 and Phase 2 audit, inspecting `agent/nodes.py` revealed that `observe_evidence` completely bypassed the raw telemetry data returned by Node 3 diagnostic tools (`fetch_logs`, `query_metrics`, `get_deployments`, `search_codebase`). Instead, it evaluated regular expressions against `state["raw_description"]`:

```python
# PRE-AUDIT FLAW (agent/nodes.py lines 75-105)
desc = state.get("raw_description", "").lower()
if "db" in desc or "pool" in desc:
    evidence.append({
        "citation": "services/payment_service.py:L66",
        "snippet": "DB pool exhausted: max_connections=10 reached",
        "classification": "supports",
        "hypothesis": "h1"
    })
    # Injected 3 synthetic supporting citations on iteration 1
```

### Impact
- **0% RCA on Natural Descriptions**: When presented with incident descriptions phrased naturally without the four exact keyword templates (e.g. `dev_007` in `eval/datasets/dev/`), the system gathered zero evidence and yielded **0 / 6 (0.0%) RCA**.
- **33.3% False Confidence Rate (FCR)**: When tested against alerts with contradictory signals (e.g., an alert description claiming a timeout while metrics showed DB pool saturation), Node 4 blindly believed the description, achieving an ungrounded 0.75 confidence score.

### Architectural Remediation
1. Rewrote `observe_evidence` in `agent/nodes.py` to iterate through `state["raw_data_refs"]`, parsing real diagnostic tool outputs:
   - `fetch_logs`: Extracts actual error/warning messages and log timestamps.
   - `query_metrics`: Inspects real gauge values (`db_connections_active`, `dependency_latency_ms`, `memory_usage_mb`, `error_rate`).
   - `get_deployments`: Inspects git commit hashes, authors, and deployment status.
   - `search_codebase`: Extracts matching file paths and AST references.
2. Implemented active contradiction detection: If metric telemetry demonstrates healthy baseline performance while an alert claims failure, an explicit contradiction record (`classification="contradicts"`) is generated.

---

## 2. Cross-Incident Telemetry State Bleed (Metrics Leakage)

### Symptom & Discovery
During initial benchmark runs across the 18 development suite cases, case `dev_004` (testing `downstream_timeout`) failed because the system unexpectedly observed high database connection saturation alongside the timeout.

### Root Cause
In `services/payment_service.py`, `_apply_fault_metrics()` only updated keys relevant to the currently active fault mode. When `db_pool_exhaustion` was triggered in an earlier test case, `db_connections_active` was set to `10`. When the subsequent case switched to `downstream_timeout`, `_apply_fault_metrics` updated `dependency_latency_ms=12000.0`, but left `db_connections_active=10` intact in `data/metrics/payment_service.json`.

### Impact
Test cases were not isolated. Incidents executed after DB pool incidents inherited stale, contaminated telemetry.

### Architectural Remediation
Updated `services/payment_service.py` to reset all 5 metric dimensions on every fault transition:
```python
if self.fault_mode == "downstream_timeout":
    self.metrics_tracker.update(
        error_rate=0.08,
        latency_ms=1200.0,
        dependency_latency_ms=12000.0,
        db_connections_active=3,       # Explicit baseline reset
        memory_usage_mb=260.0          # Explicit baseline reset
    )
```
In addition, `reset_service_logs()` was introduced into `eval/run_benchmark.py` to truncate active log files between evaluations.

---

## 3. Silent Log Filtering (Hiding Memory Leak Warning Indicators)

### Symptom & Discovery
`dev_003` (Memory Leak) failed to corroborate log evidence despite the microservice logging memory pressure.

### Root Cause
`tools/fetch_logs.py` filtered log lines using a strict equality check:
```python
# PRE-AUDIT FILTER
if level and entry.get("level", "").upper() != level.upper():
    continue
```
Because the agent requested `level="ERROR"`, and the simulated service logged memory exhaustion as `level="WARNING"` (`"High memory usage detected: heap utilized > 90%"`), `fetch_logs` silently dropped all memory leak log entries.

### Impact
The agent was unable to extract log corroboration for memory leaks, preventing multi-source corroboration.

### Architectural Remediation
Modified `tools/fetch_logs.py` to include actionable warning indicators when error logs are requested:
```python
target_levels = {"ERROR", "WARN", "WARNING"} if level.upper() in ["ERROR", "WARN", "WARNING"] else {level.upper()}
if entry_level not in target_levels:
    continue
```

---

## 4. Cryptographic Citation Drift & Out-of-Bounds References

### Symptom & Discovery
In the baseline implementation, citations were stored as static strings (e.g. `services/payment_service.py:L66`). When `services/payment_service.py` was modified to fix the metric state bleed bug, line 66 shifted from `"DB pool exhausted..."` to `dependency_latency_ms=20.0`.

### Impact
In real engineering repositories, code drifts continuously. Static line references rot, leading to false citations, broken links, and audit failures.

### Architectural Remediation
Implemented `CitationValidator` (`agent/citation.py`) with a 3-tier validation hierarchy:
1. **Level 1 (Existence)**: Verifies that the source file exists and line bounds are within total line count.
2. **Level 2 (Content Match & Hash Drift)**: Compares the snippet against the file line and verifies a 16-character SHA-256 hash (`snippet_hash`). If the line shifted or the text changed, a `drift detected` failure is raised.
3. **Level 3 (Semantic Grounding)**: Deterministically validates that snippet terms corroborate the hypothesis fault mode.

---

## 5. Binary Status Schema Inability to Represent Active Contradictions

### Symptom & Discovery
The legacy schema only supported `sufficient_confidence` and `insufficient_evidence`. When an incident featured contradictory telemetry (e.g. an alert claiming a payment gateway timeout while metrics showed 0.0 error rate and 10 active DB connections), the system had no valid terminal state.

### Impact
The system either falsely diagnosed the incident or mischaracterized an active conflict as "missing data".

### Architectural Remediation
Refactored the state machine to 4 explicit SRE terminal states:
- `resolved`: Evidence $\ge 0.75$, no active contradictions.
- `insufficient_evidence`: Max iterations reached, evidence $< 0.75$, no active contradictions.
- `unresolved_conflict`: Contradictory evidence signals remain unresolved after diagnostic tools have completed.
- `failed`: Systemic tool or infrastructure errors occurred during investigation (`degraded: true`).

---

## 6. SRE Evaluation Summary Matrix

| Failure Mode | Pre-Audit Vulnerability | Post-Hardening Defense | Validated Test Case / Metric |
|---|---|---|---|
| **Natural Language Alerts** | 0% RCA (Failed on any phrasing variation) | Ingests real tool payloads (`raw_data_refs`) | `dev_001` - `dev_006` (100% RCA) |
| **Telemetry State Bleed** | DB metrics contaminated subsequent test cases | Explicit 5-dimensional baseline reset | Multi-case benchmark run |
| **Silent Log Filter** | Blind to memory leak `WARNING` logs | Broadened level filter to include `WARN`/`WARNING` | `dev_003`, `holdout_003` |
| **Citation Drift** | Static `:L66` line references broke upon edits | SHA-256 snippet hashing & 3-level validator | `tests/test_citation_validator.py` |
| **Contradictory Telemetry** | 33.3% False Confidence Rate (FCR) | Dedicated `unresolved_conflict` terminal state | `dev_010` - `dev_012` (0% FCR) |
| **Missing Diagnostics** | Blindly guessed root cause | `insufficient_evidence` state with `degraded` flag | `dev_016` - `dev_018` (100% CAR) |
