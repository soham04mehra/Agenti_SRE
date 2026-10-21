# Agentic SRE Incident Investigation & Recommendation Platform

An agentic decision-support platform designed to investigate production service degradations and incident alerts. Built on a **stateful LangGraph workflow**, multi-modal diagnostic tool execution, **Supabase vector persistence**, and a **deterministic evidence-grounding engine**, the system identifies root causes, verifies forensic citations cryptographically, detects conflicting telemetry, and recommends actionable remediation — with explicit uncertainty states when evidence is ambiguous.

> **Decision support, not auto-remediation.** The platform investigates telemetry, correlates signals across observability silos, and recommends remediation backed by tamper-evident citations. It never executes mutating production actions autonomously.

🌐 **Live Production Console**: [https://agenti-sre.vercel.app](https://agenti-sre.vercel.app)

---

## Table of Contents

- [Core Principles & Engineering Trade-offs](#core-principles--engineering-trade-offs)
- [System Architecture & 6-Stage Graph Workflow](#system-architecture--6-stage-graph-workflow)
- [Explicit SRE State Machine & Uncertainty Routing](#explicit-sre-state-machine--uncertainty-routing)
- [Deterministic Evidence Sufficiency Scoring](#deterministic-evidence-sufficiency-scoring)
- [3-Level Cryptographic Citation Validation](#3-level-cryptographic-citation-validation)
- [Diagnostic Tool Orchestration](#diagnostic-tool-orchestration)
- [Execution Tracing & Cost Accounting](#execution-tracing--cost-accounting)
- [Evaluation Rigor: Baseline vs. Hardened Benchmark](#evaluation-rigor-baseline-vs-hardened-benchmark)
- [Technical Interview FAQ & System Defenses](#technical-interview-faq--system-defenses)
- [Database Schema & Local Fallback](#database-schema--local-fallback)
- [Local Setup & Running Tests](#local-setup--running-tests)

---

## Core Principles & Engineering Trade-offs

| Principle | Architectural Implementation | Practical Trade-off |
|---|---|---|
| **Deterministic Grounding** | State transitions and confidence scores use mathematical formulas and concrete tool output assertions rather than stochastic LLM prompts. | Eliminates prompt hallucination and scoring drift, but requires formalizing telemetry schemas. |
| **Tamper-Evident Citations** | Every piece of evidence captures line bounds, source paths, and a 16-character SHA-256 snippet hash (`snippet_hash`). | Detects code drift and false citations across commits, but requires file-level read access. |
| **Explicit Uncertainty States** | Distinguishes between `resolved`, `insufficient_evidence`, `unresolved_conflict`, and `failed`. | Avoids forced, misleading root-cause guesses under ambiguity, but requires downstream consumers to handle non-terminal abstentions. |
| **Sub-Millisecond Engine Latency** | Graph traversal and telemetry evaluation run in ~1.4ms locally. | LLM invocation is reserved for unstructured parsing and synthesis, preventing latency inflation during diagnostic tool loops. |

---

## System Architecture & 6-Stage Graph Workflow

Core logic lives in [`agent/graph.py`](file:///Users/sohammehra/documents/PROJECTS/Agentic%20sre%20/agent/graph.py) and [`agent/nodes.py`](file:///Users/sohammehra/documents/PROJECTS/Agentic%20sre%20/agent/nodes.py) as a stateful 6-node LangGraph pipeline:

```
[ Alert Received ]
        │
        ▼
01: understand_incident ────► Extracts service, symptom, severity
        │
        ▼
02: plan_investigation  ◄───┐ Selects diagnostic tools based on loop iteration
        │                   │
        ▼                   │
03: execute_tools           │ Invokes tools via registry (Logs, Metrics, Git, Code)
        │                   │
        ▼                   │
04: observe_evidence        │ Extracts telemetry assertions & calculates SHA-256 hashes
        │                   │
        ▼                   │
05: evaluate_confidence     │ Computes S = S / (S + C + 1); determines state
        │                   │
        ├─ status == "investigating" ──► (Loop back, max 3 iterations)
        │
        └─ Terminal Status: resolved | insufficient_evidence | unresolved_conflict | failed
        │
        ▼
06: generate_report ────────► Formats structured SRE RCA report with action items
```

### Node Descriptions

1. **`understand_incident`**: Normalizes alert payloads into structured metadata (`affected_service`, `symptom`, `severity`).
2. **`plan_investigation`**: Dynamic loop controller (max 3 loops). Initializes 4 fault hypotheses and schedules diagnostic tools:
   - *Loop 1 (Telemetry)*: `fetch_logs`, `query_metrics`
   - *Loop 2 (Code & Releases)*: `get_deployments`, `search_codebase`
   - *Loop 3 (Historical Memory)*: `retrieve_similar_incidents` (Supabase vector similarity)
3. **`execute_tools`**: Invokes diagnostic tools and stores structured payloads in `raw_data_refs`.
4. **`observe_evidence`**: Parses actual tool outputs, tags evidence with source modalities (`logs`, `metrics`, `deployments`, `codebase`), and validates cryptographic hashes.
5. **`evaluate_confidence`**: Evaluates the evidence sufficiency heuristic, detects contradictions, and routes the graph.
6. **`generate_report`**: Synthesizes the final SRE report, grouping evidence by modality and presenting actionable remediation steps.

---

## Explicit SRE State Machine & Uncertainty Routing

Rather than forcing a binary outcome (`success` / `failure`), the agent implements 4 explicit terminal states and an observability degradation flag:

```python
# agent/state.py
Status = Literal[
    "investigating",        # Active diagnostic loop
    "resolved",             # S >= 0.75 with zero unresolved contradictions
    "insufficient_evidence",# Loop limit reached without sufficient signal
    "unresolved_conflict",  # Contradictory signals remain unresolvable
    "failed"                # Systemic tool or infrastructure errors
]
```

### Deterministic Routing Rules (`route_after_confidence`)

- $S \ge 0.75$ and zero contradictions $\rightarrow$ `generate_report` (`status = "resolved"`)
- Active contradictions on top hypothesis $\rightarrow$ `generate_report` (`status = "unresolved_conflict"`)
- Systemic tool execution failure $\rightarrow$ `generate_report` (`status = "failed"`, `degraded = True`)
- $S < 0.75$ and `iteration_count < 3` $\rightarrow$ Loop back to `plan_investigation` (`status = "investigating"`)
- $S < 0.75$ and `iteration_count >= 3` $\rightarrow$ `generate_report` (`status = "insufficient_evidence"`)

---

## Deterministic Evidence Sufficiency Scoring

Implemented in [`agent/confidence.py`](file:///Users/sohammehra/documents/PROJECTS/Agentic%20sre%20/agent/confidence.py). Scores are computed using a deterministic heuristic, not an uncalibrated LLM probability estimate:

$$S = \min\left(0.95, \frac{\text{Supports}}{\text{Supports} + \text{Contradicts} + 1.0} \times (0.7 \text{ if Contradicts} > 0)\right)$$

### Mathematical Calibration & Boundary Behavior

| Supporting Items ($S$) | Contradicting Items ($C$) | Raw Formula | With Penalty ($0.7\times$) | Final Score | Terminal Outcome |
|---|---|---|---|---|---|
| 0 | 0 | $0 / 1.0 = 0.00$ | N/A | **0.00** | `insufficient_evidence` |
| 1 | 0 | $1 / 2.0 = 0.50$ | N/A | **0.50** | `investigating` |
| 2 | 0 | $2 / 3.0 = 0.67$ | N/A | **0.67** | `investigating` |
| **3** | **0** | **$3 / 4.0 = 0.75$** | **N/A** | **0.75** | **`resolved` (Threshold boundary)** |
| 4 | 0 | $4 / 5.0 = 0.80$ | N/A | **0.80** | `resolved` |
| 3 | 1 | $3 / 5.0 = 0.60$ | $0.60 \times 0.7$ | **0.42** | `unresolved_conflict` |
| 50 | 0 | $50 / 51.0 = 0.98$ | Capped at 0.95 | **0.95** | `resolved` (Upper bound cap) |

> **Why call it an "Evidence Sufficiency Score" rather than "Confidence"?**
> Calling this metric "confidence" invites the question *"calibrated against what probability distribution?"* In this system, $S \ge 0.75$ means exactly **three uncontradicted pieces of evidence**. Calling it an evidence sufficiency score clearly communicates the deterministic threshold policy.

---

## 3-Level Cryptographic Citation Validation

Implemented in [`agent/citation.py`](file:///Users/sohammehra/documents/PROJECTS/Agentic%20sre%20/agent/citation.py), the platform protects against hallucinated and drifting citations across code commits:

1. **Level 1 (Existence)**: Verifies file existence on disk (or registered virtual source) and confirms line bounds are within total line counts.
2. **Level 2 (Content Match & Drift Detection)**: Verifies that snippet text matches the file content. Compares the stored 16-character SHA-256 hash (`snippet_hash`). If code was modified or refactored, the validator raises an explicit `drift detected` failure.
3. **Level 3 (Semantic Grounding)**: Deterministically validates that evidence terms corroborate the specific fault mode signature.

---

## Diagnostic Tool Orchestration

Registered in [`tools/registry.py`](file:///Users/sohammehra/documents/PROJECTS/Agentic%20sre%20/tools/registry.py):

| Tool | Signature | Modality | Output Payload |
|---|---|---|---|
| `fetch_logs` | `(service_name: str, level: str = "ERROR", lines: int = 50)` | Logs | Parsed JSON log events with timestamps and log levels. |
| `query_metrics` | `(service_name: str)` | Metrics | Active telemetry gauges: `db_connections_active`, `latency_ms`, `error_rate`, `memory_usage_mb`, `dependency_latency_ms`. |
| `get_deployments` | `(service_name: str)` | Deployments | Commit SHA, deploy timestamp, author, and configuration diffs. |
| `search_codebase` | `(query: str, path_filter: Optional[str])` | Codebase | Source file matches, AST line references, and code context. |
| `retrieve_similar_incidents` | `(query: str, match_threshold: float = 0.7)` | Vector DB | Cosine similarity lookup via Supabase `pgvector` RPC. |

---

## Execution Tracing & Cost Accounting

Implemented in [`agent/tracer.py`](file:///Users/sohammehra/documents/PROJECTS/Agentic%20sre%20/agent/tracer.py). Every investigation records a structured execution trace:

- **Per-Node Spans**: Measures duration (ms) for all 6 workflow nodes.
- **Tool Spans**: Measures individual tool execution latencies and arguments.
- **Cost Calculation**: Computes exact API list-price costs based on prompt and completion token counts:
  $$\text{Cost} = \left(\frac{N_{\text{prompt}}}{1000} \times \$0.00015\right) + \left(\frac{N_{\text{comp}}}{1000} \times \$0.00060\right)$$
- **Trace Output**: Embedded in benchmark results and incident database records for observability audits.

---

## Evaluation Rigor: Baseline vs. Hardened Benchmark

### Historical Baseline Audit (`baseline-v0`, Tagged at Commit `3eaffd9`)

The initial pre-audit codebase evaluated against 24 synthetic single-fault incidents across 4 fault modes.
- **Audit Findings**: The baseline Node 4 relied on regex substring checks over `state["raw_description"]` rather than inspecting tool outputs.
- When tested against natural descriptions without exact keywords, root cause accuracy was **0.0%**.
- When tested against contradictory alerts, the false-confidence rate was **33.3%**.

### Hardened Robustness Benchmark (36 Cases Across 6 Categories)

The benchmark was expanded to 36 structured test cases across 6 realistic failure modalities, partitioned into an 18-case development suite and an 18-case frozen holdout suite tagged `holdout-v1`:

1. `clear_diagnosis` (6 cases): Definitive fault telemetry.
2. `insufficient_evidence` (6 cases): Vague alert, normal telemetry.
3. `noisy_evidence` (6 cases): Background warnings alongside real faults.
4. `conflicting_evidence` (6 cases): Alert text contradicts telemetry.
5. `red_herring` (6 cases): Cosmetic error without service impact.
6. `missing_diagnostic_source` (6 cases): Tool downtime / missing data.

### Measured Benchmark Results

| Metric | Formal Definition | Development Suite (18 Cases) | Frozen Holdout (`holdout-v1`, 18 Cases) |
|---|---|---|---|
| **Root-Cause Accuracy (RCA)** | $\frac{\text{Correct Definite Diagnoses}}{\text{Total Diagnostic Cases}}$ | **6 / 6 (100.0%)** | **6 / 6 (100.0%)** |
| **Correct Abstention Rate (CAR)** | $\frac{\text{Safe Abstentions}}{\text{Total Non-Diagnostic Cases}}$ | **12 / 12 (100.0%)** | **12 / 12 (100.0%)** |
| **False-Confidence Rate (FCR)** | $\frac{\text{Hallucinated Diagnoses on Ambiguous Cases}}{\text{Total Non-Diagnostic Cases}}$ | **0 / 12 (0.0%)** | **0 / 12 (0.0%)** |
| **Citation Validity (CVR L1)** | $\frac{\text{Verified Grounded Citations}}{\text{Total Citations Generated}}$ | **50 / 50 (100.0%)** | **48 / 48 (100.0%)** |
| **Investigation Efficiency (IE)** | $\text{Mean diagnostic loop count per incident}$ | **2.44 loops** | **2.39 loops** |
| **Avg In-Memory Latency** | $\text{Mean graph traversal latency (local)}$ | **~1.4 ms** | **~1.5 ms** |

---

## Technical Interview FAQ & System Defenses

### 1. "Why use a deterministic heuristic formula instead of an LLM judge for confidence?"
> **Answer**: LLM confidence scores are uncalibrated and non-deterministic; identical prompts can yield 0.85 on one run and 0.65 on the next. In an SRE decision-support system, an engineer needs to know *why* an incident crossed the threshold. Our formula $S / (S + C + 1)$ is transparent: $S \ge 0.75$ means exactly three uncontradicted supporting citations. Contradictions explicitly dock the score.

### 2. "What prevents 10 identical log error lines from inflating confidence to 95%?"
> **Answer**: Evidence is deduplicated by semantic summary and snippet content before ingestion. Furthermore, `CitationRecord.infer_source_type` groups evidence into distinct observability modalities (`logs`, `metrics`, `deployments`, `codebase`). A single repeating log line only yields one evidence record; reaching 0.75 requires corroboration across multiple independent telemetry sources.

### 3. "How do you protect against citation drift when code changes?"
> **Answer**: Static line references (e.g. `file.py:L66`) rot immediately when lines are added or removed. `agent/citation.py` generates a 16-character SHA-256 hash of the normalized snippet at citation time. When verified, the validator checks both line bounds and snippet hash consistency, immediately flagging `drift detected` if the code was modified.

### 4. "Where does the LLM actually fit into this architecture?"
> **Answer**: The LLM is used where natural language reasoning is required: parsing unstructured alert notifications into structured service/symptom schemas (Node 1) and generating natural-language incident summaries for human SREs (Node 6). Diagnostic tool execution, evidence classification, contradiction detection, and graph routing are kept strictly deterministic to prevent hallucinations and uncalibrated routing.

---

## Database Schema & Local Fallback

Postgres (Supabase) + `pgvector`, implemented in [`database/connection.py`](file:///Users/sohammehra/documents/PROJECTS/Agentic%20sre%20/database/connection.py) and [`database/repository.py`](file:///Users/sohammehra/documents/PROJECTS/Agentic%20sre%20/database/repository.py). **Automatically falls back to local in-memory storage** when Supabase credentials are not present in `.env`.

```sql
-- Incident Execution State Store
CREATE TABLE IF NOT EXISTS incident_state (
    incident_id TEXT PRIMARY KEY,
    raw_description TEXT NOT NULL,
    affected_service TEXT,
    symptom TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    status TEXT DEFAULT 'investigating',
    state_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Historical Incident Vector Store
CREATE TABLE IF NOT EXISTS past_incidents (
    past_incident_id TEXT PRIMARY KEY,
    symptom TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    resolution TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## Local Setup & Running Tests

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/sohammehra/Agentic-sre.git
cd "Agentic-sre"

# Install dependencies
pip install -r requirements.txt

# Configure environment variables (optional; falls back to in-memory mode)
cp .env.example .env
```

### 2. Run Pure Unit Test Suite

```bash
# Runs all 26 unit tests (confidence boundaries, state transitions, citation validators, tracers)
python -m unittest discover tests
```

### 3. Run Robustness Benchmarks

```bash
# Run Development Benchmark (18 cases)
python eval/run_benchmark.py --suite dev

# Run Frozen Holdout Benchmark (18 cases)
python eval/run_benchmark.py --suite holdout
```

### 4. Start Local Development Server

```bash
# Launches FastAPI app and serves Web Console on http://localhost:8000
python api.py
```
