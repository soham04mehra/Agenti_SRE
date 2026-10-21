# EVALUATION.md — Formal Evaluation Framework & Benchmark Specification

**Specification Version**: 1.0.0  
**Status**: ACTIVE / FROZEN FOR BENCHMARKING  
**Target Suite**: Robustness Evaluation Benchmark (36 Cases)  

---

## 1. Overview & Evaluation Philosophy

The objective of this evaluation suite is to rigorously test whether the Agentic SRE system can:
1. Reason over diagnostic evidence (logs, metrics, deployments, code) rather than memorizing static keywords.
2. Formulate correct root-cause diagnoses when evidence is conclusive.
3. Explicitly abstain (`insufficient_evidence` or `unresolved_conflict`) when evidence is incomplete, ambiguous, or contradictory.
4. Tolerate noisy, irrelevant background telemetry without false attribution.
5. Operate reliably in degraded observability environments (e.g., missing metrics or unreadable logs).

To guarantee scientific validity, the benchmark separates **Development/Tuning Cases** from an **Immutable Frozen Holdout**.

---

## 2. Dataset Architecture & Split

The suite comprises **36 structured incident cases** divided equally into two isolated sets:

| Category | Description | Dev Cases | Holdout Cases | Total | Expected Status |
|---|---|---|---|---|---|
| **`clear_diagnosis`** | Definitive evidence present across logs, metrics, or deployment diffs. | 3 (`dev_001`–`003`) | 3 (`hold_001`–`003`) | 6 | `resolved` |
| **`insufficient_evidence`** | Vague alert symptom, normal baseline metrics, no error signatures. | 3 (`dev_004`–`006`) | 3 (`hold_004`–`006`) | 6 | `insufficient_evidence` |
| **`noisy_evidence`** | Real fault accompanied by benign background warnings / unrelated noise. | 3 (`dev_007`–`009`) | 3 (`hold_007`–`009`) | 6 | `resolved` |
| **`conflicting_evidence`** | Alert claims one cause but telemetry directly contradicts it or points elsewhere. | 3 (`dev_010`–`012`) | 3 (`hold_010`–`012`) | 6 | `unresolved_conflict` / `insufficient_evidence` |
| **`red_herring`** | Isolated benign warning with completely healthy systemic metrics. | 3 (`dev_013`–`015`) | 3 (`hold_013`–`015`) | 6 | `insufficient_evidence` |
| **`missing_diagnostic_source`** | Diagnostic source unavailable (e.g. metrics 404 or empty log). | 3 (`dev_016`–`018`) | 3 (`hold_016`–`018`) | 6 | `insufficient_evidence` (degraded) |
| **TOTAL** | | **18** | **18** | **36** | |

### Holdout Freezing Policy (Rule 3)
* The **18 Holdout Cases** (`eval/datasets/holdout/`) are frozen immediately upon review and tagged in git (`holdout-v1`).
* **Zero Modification Rule**: Holdout cases shall never be modified, deleted, re-labeled, or tuned against during development.
* Tuning experiments are strictly restricted to the **18 Development Cases** (`eval/datasets/dev/`).

---

## 3. Case Schema Specification

Every case is stored as a self-contained JSON file conforming to this exact schema:

```json
{
  "case_id": "dev_001",
  "incident_description": "Production checkout API latency spiking to 8.2s with HTTP 504 gateway errors under peak traffic load.",
  "category": "clear_diagnosis",
  "affected_service": "payment_service",
  "expected_status": "resolved",
  "expected_root_cause": "downstream_timeout",
  "allowed_root_causes": ["downstream_timeout", "external_gateway_timeout", "dependency_latency"],
  "supporting_evidence": [
    "GatewayTimeout: Call to external payment gateway timed out after 30000ms",
    "dependency_latency_ms=30000.0"
  ],
  "contradicting_evidence": [],
  "expected_tool_sources": ["fetch_logs", "query_metrics"],
  "difficulty": "medium",
  "degraded_expected": false
}
```

---

## 4. Formal Metric Definitions

All metrics are reported as **exact counts with denominators** (e.g., `15 / 18`) alongside percentage representations.

### Metric 1: Root-Cause Accuracy (RCA)
Evaluates whether the system correctly diagnoses the root cause.  
**Applicability**: Evaluated **only** on cases where a definitive diagnosis is expected (`category in ["clear_diagnosis", "noisy_evidence"]`).
$$\text{RCA} = \frac{\sum_{i \in \text{DiagnosticCases}} \mathbb{I}(\text{diagnosis}_i \in \text{allowed\_causes}_i)}{|\text{DiagnosticCases}|}$$

### Metric 2: Correct Abstention Rate (CAR)
Evaluates whether the system correctly refrains from guessing when evidence is insufficient, benign, or contradictory.  
**Applicability**: Evaluated on cases where the expected status is non-resolved (`category in ["insufficient_evidence", "red_herring", "conflicting_evidence", "missing_diagnostic_source"]`).
$$\text{CAR} = \frac{\sum_{j \in \text{AbstentionCases}} \mathbb{I}(\text{status}_j \in \{\texttt{"insufficient\_evidence"}, \texttt{"unresolved\_conflict"}\})}{|\text{AbstentionCases}|}$$

### Metric 3: False-Confidence Rate (FCR)
Measures safety failure: when the system claims a definitive diagnosis on an incident that should have triggered abstention or where evidence is contradicted.
$$\text{FCR} = \frac{\sum_{k \in \text{AbstentionCases}} \mathbb{I}(\text{status}_k == \texttt{"resolved"})}{|\text{AbstentionCases}|}$$
*Target: Strictly 0 / N (zero false alarms on ambiguous/benign inputs).*

### Metric 4: Citation Validity Rate (CVR)
Evaluated across three independent levels:
1. **Level 1 (Existence)**: Does the cited file path exist on disk?
   $$\text{CVR}_{\text{exist}} = \frac{|\text{Citations with valid file path}|}{|\text{Total Citations}|}$$
2. **Level 2 (Content Match)**: Does the cited snippet or pattern actually exist within the referenced file?
   $$\text{CVR}_{\text{content}} = \frac{|\text{Citations whose content exists in file}|}{|\text{Total Citations}|}$$
3. **Level 3 (Semantic Support)**: Does the evidence factually support the assigned hypothesis classification (`supports` vs `contradicts`)?
   $$\text{CVR}_{\text{semantic}} = \frac{|\text{Citations correctly classified}|}{|\text{Total Citations}|}$$

### Metric 5: Investigation Efficiency (IE)
Measures investigation economy:
* **Average Iterations per Incident**: $\bar{I} = \frac{1}{N} \sum_{i=1}^N \text{iterations}_i$ (bounded between $1.0$ and $3.0$).
* **Tool Call Count**: Average number of distinct diagnostic tool executions per incident.

---

## 5. Execution & Stochasticity Controls (Phase 2E)

When invoking generative LLMs during evaluation:
1. **Temperature**: Strictly fixed at `temperature = 0.0` for reproducibility.
2. **Multi-Run Variance**: For non-deterministic components, benchmark runs are executed 3 times per case, reporting mean and variance.
3. **Execution Mode**: Evaluated locally via CLI (`python -m eval.run`) to decouple benchmarking from HTTP gateway/Vercel request timeout boundaries.
