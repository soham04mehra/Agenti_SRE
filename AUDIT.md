# AUDIT.md — Comprehensive Repository & Architecture Audit

**Target System**: Agentic SRE Incident Investigation & Recommendation Platform  
**Audit Date**: 2026-10-21  
**Baseline Commit**: `3eaffd917ca153ca347c89d42c1b5a0a4e2cb6e1`  
**Git Tag**: `baseline-v0`  
**Auditor**: Senior Systems & AI Evaluation Audit  

---

## 1. README Claims vs. Implementation Reality

| README Claim | Status | Evidence | File / Line | Notes |
|---|---|---|---|---|
| **"Autonomous decision-support system"** | **OVERSTATED** | The workflow is a fixed state machine driven by deterministic keyword substring checks on the input description. No autonomous planning occurs. | `agent/nodes.py:93-123` | Labeled "autonomous", but tool selection and evidence generation follow hardcoded branching. |
| **"6-stage LangGraph workflow"** | **TRUE** | StateGraph with 6 nodes (`understand_incident`, `plan_investigation`, `execute_tools`, `observe_evidence`, `evaluate_confidence`, `generate_report`) and conditional routing is fully defined. | `agent/graph.py:24-56` | LangGraph structure is genuinely implemented and compiled. |
| **"Diagnostic tool execution via Model Context Protocol (MCP)"** | **OVERSTATED** | `mcp>=1.0.0` is present in `requirements.txt`, but tools are local Python functions called via standard dictionary dispatch (`TOOL_REGISTRY`). No MCP client/server protocol is used. | `tools/registry.py:8-29`, `requirements.txt:20` | Native Python function dispatch mislabeled as MCP protocol execution. |
| **"Supabase vector persistence"** | **OVERSTATED** | Supabase connection defaults to `local_fallback` mode because `.env` holds dummy credentials. The database query function does a flat `.select().limit(3)` rather than vector similarity search. | `database/connection.py:8-15`, `database/repository.py:47-66` | No pgvector embedding generation or vector similarity RPC is executed during runtime. |
| **"Deterministic confidence scoring engine"** | **OVERSTATED** | The formula $S = \frac{\text{Supports}}{\text{Supports} + \text{Contradicts} + 1}$ is an uncalibrated Laplace-smoothed heuristic ratio. $S \ge 0.75$ with 0 contradictions simply equates to requiring $\ge 3$ pieces of evidence. | `agent/confidence.py:24-34` | Heuristic evidence ratio marketed as a formal "confidence scoring engine". |
| **"Decision support only; never auto-remediates"** | **TRUE** | System only returns JSON reports with recommended runbook actions; no write access or mutation capabilities exist. | `agent/nodes.py:160-180`, `api.py:51-90` | Strictly read-only boundary is maintained throughout. |
| **"Sub-second SLA: in-memory iterations under 300ms"** | **OVERSTATED** | In-memory iterations complete in ~0.0s (measured avg 0.00s) solely because the LLM is completely bypassed and tools read local mock files. | `eval/evaluate.py:65`, `eval/baseline_v0_raw.json` | Presenting pure string matching speed as an "AI agent SLA" without noting LLM omission is misleading. |
| **"Awwwards-level UI"** | **OVERSTATED** | Modern, clean dark-themed Tailwind CSS React dashboard, but promotional marketing jargon. | `static/index.html:14-76` | Subjective design claim; lacks grounding in technical capability. |
| **"100.0% Root Cause Accuracy"** | **OVERSTATED** | Node 4 hardcodes the exact 3 evidence items based on string matching against `raw_description` keywords ("db pool", "v2.4.1", "memory", "30s"), guaranteeing a 100% score on the 24 synthetic cases. | `agent/nodes.py:93-124`, `eval/evaluate.py:80-92` | 100% accuracy is an artifact of evaluation leakage and input keyword hardcoding. |
| **"100.0% Retrieval Recall & Precision"** | **FALSE** | `eval/evaluate.py` does not measure vector retrieval. It calculates `len(supports) / len(expected_evidence)`, which equals $3 / 3 = 100\%$ because Node 4 hardcodes 3 supporting items. Vector retrieval is never called. | `eval/evaluate.py:98-109` | Evidence item counting was misreported as RAG retrieval precision/recall. |
| **"0.0% False Confidence Rate"** | **OVERSTATED** | The benchmark contains 0 ambiguous cases, 0 conflicting cases, and 0 cases lacking evidence. With only clear ground-truth cases, false confidence was structurally impossible. | `ground_truths/eval_inc_*.json`, `eval/evaluate.py:94-96` | Trivial metric achievement due to lack of negative/abstention cases. |
| **"Zero unverified AI hallucination"** | **OVERSTATED** | The LLM (`gpt-4o-mini`) is never invoked inside the investigation loop. The system did not hallucinate because no generative model was executed. | `agent/nodes.py:4`, `agent/llm.py:8-12` | Absence of model invocation presented as an algorithmic hallucination prevention mechanism. |

---

## 2. PHASE 1A — LLM Audit Table

| Node | Invokes LLM? | Model | Input | Output | Deterministic Logic | Effect on System State |
|---|---|---|---|---|---|---|
| **Node 1: `understand_incident`** | **NO** | None (imported, unused) | `raw_description` string | `affected_service`, `symptom`, `severity`, `status` | Checks if `"payment"` or `"order"` in `raw_description.lower()`. | Sets `affected_service = "payment_service"`, `status = "investigating"`. |
| **Node 2: `plan_investigation`** | **NO** | None | `iteration_count`, `hypotheses` | `iteration_count + 1`, 4 static hypotheses, `next_tool_calls` | Increments iteration count. Fixed tool schedule: Loop 1 $\rightarrow$ logs/metrics, Loop 2 $\rightarrow$ deploy/code, Loop 3 $\rightarrow$ RAG. | Initializes 4 fixed hypotheses ($h_1 \dots h_4$) and next tool list. |
| **Node 3: `execute_tools`** | **NO** | None | `next_tool_calls`, `affected_service` | `tools_called`, `raw_data_refs` | Dispatches tool names via Python `TOOL_REGISTRY`. Reads static local files or runs regex search. | Populates tool output data in state. |
| **Node 4: `observe_evidence`** | **NO** | None | `raw_description` | `evidence` list (3 items) | **Keyword bypass**: inspects `raw_description` for substrings (`"db pool"`, `"v2.4.1"`, `"memory"`, `"gateway timeout"`). Bypasses tool outputs. | Directly appends 3 hardcoded supporting evidence citations. |
| **Node 5: `evaluate_confidence`** | **NO** | None | `hypotheses`, `evidence` | `confidence_score`, `status` | Calculates $S = \frac{\text{Supports}}{\text{Supports} + \text{Contradicts} + 1}$. If $S \ge 0.75 \rightarrow$ `sufficient_confidence`. | Sets score to $0.75$, status to `sufficient_confidence`. Triggers router exit. |
| **Node 6: `generate_report`** | **NO** | None | `hypotheses`, `evidence`, `status` | `final_report` dict | Template string formatting selecting top hypothesis by score. | Sets `final_report` dictionary with static remediation strings. |

**Key Finding**: The LLM (`gpt-4o-mini` via `ChatOpenAI`) is instantiated in `agent/llm.py` and imported on line 4 of `agent/nodes.py`, but **it is never called anywhere in the graph**. The entire pipeline executes as a deterministic rule-based script.

---

## 3. PHASE 1B — Deterministic Logic Audit

1. **Iteration Limits**: Capped at `max_iterations = 3`. However, because Node 4 injects 3 supporting evidence items on iteration 1, the confidence always hits $0.75$ on Loop 1. Iterations 2 and 3 are never reached in normal execution.
2. **Routing (`route_after_confidence`)**:
   - `status in ["sufficient_confidence", "insufficient_evidence"]` $\rightarrow$ `generate_report`
   - Else $\rightarrow$ `replan` (loops back to `plan_investigation`).
   - Purely deterministic Python function based on state dictionary values.
3. **Scoring (`agent/confidence.py`)**:
   - Formula: $S = \frac{\text{Supports}}{\text{Supports} + \text{Contradicts} + 1}$
   - Penalty: $S = S \times 0.7$ if `contradicts > 0`.
   - Cap: $\min(S, 0.95)$, rounded to 2 decimal places.
   - Behavior: 3 supports, 0 contradicts $\rightarrow \frac{3}{3 + 0 + 1} = 0.75$.
4. **Tool Execution (`tools/registry.py`)**:
   - Direct function pointer map. No network calls or MCP protocol envelopes.
   - `get_deployments.py` returns hardcoded commit `v2.4.1` with `PAYMENT_GATEWAY_URL: "http://invalid-host:9999"` regardless of input.
   - `retrieve_similar_incidents.py` queries local memory fallback returning static incident `inc_past_001`.
5. **Benchmark Scoring (`eval/evaluate.py`)**:
   - Checks root cause via substring matching: `"db"` / `"pool"` / `"connection"` for DB pool exhaustion, `"deployment"` / `"config"` / `"url"` for bad deployment, etc.
   - Computes precision and recall by counting evidence items rather than comparing against expected evidence content.

---

## 4. PHASE 1C — Label Leakage Audit

### Critical Finding: Direct Label Leakage in Multiple Layers

1. **Input Description Keyword Coupling**:
   - `eval/generate_dataset.py` generates descriptions containing explicit keywords:
     - Scenario 1 contains `"database connection acquisition timeout"` $\rightarrow$ matched in `agent/nodes.py:93`.
     - Scenario 2 contains `"deployment release v2.4.1"` and `"100% error rate"` $\rightarrow$ matched in `agent/nodes.py:101`.
     - Scenario 3 contains `"heap memory usage"` and `"climbing"` $\rightarrow$ matched in `agent/nodes.py:109`.
     - Scenario 4 contains `"gateway timeout"` and `"30s"` $\rightarrow$ matched in `agent/nodes.py:117`.
2. **Bypass of Diagnostic Tools**:
   - Node 4 (`observe_evidence`) does not parse the output of Node 3 (`execute_tools`). Instead, it inspects `state["raw_description"]`. Even if tool execution returned empty or invalid data, Node 4 produces the exact same 3 supporting citations based entirely on the alert text.
3. **Direct Fault Mode Injection in Logs**:
   - `data/logs/order_service.log` line 1: `{"message": "Order service fault mode updated", "fault_mode": "db_pool_exhaustion"}`
   - `data/logs/payment_service.log` line 1: `{"message": "Fault mode updated", "fault_mode": "db_pool_exhaustion"}`
   - The ground-truth internal enum name is written directly into the log stream.

---

## 5. PHASE 1D — Retrieval Leakage Audit

### Leave-One-Out Retrieval Analysis
- **Total Test Cases**: 24 synthetic incidents.
- **RAG Execution Status**: **0 of 24 cases executed vector retrieval**.
- **Reason**: The loop terminates at iteration 1 because confidence reaches $0.75$. Vector retrieval is only scheduled for loop 3 (`current_iteration == 3`).
- **Corpus State**:
  - Supabase client is disconnected (`None`).
  - Local memory store contains exactly 1 static entry (`inc_past_001`).
  - The 24 evaluation incidents are NOT stored in `past_incidents`.
- **Retrieval Result**:
  - Original retrieval recall/precision claim: **100.0%**.
  - Actual vector retrieval performed: **None (0 calls)**.
  - Conflation: The evaluation script labeled evidence classification counts (`relevant / expected`) as "retrieval recall/precision".

---

## 6. PHASE 1E — Secrets & Security Audit

1. **Git-Tracked `.env` File**:
   - `.env` was committed in commit `e511ed0b4ebd526f8eb29b49fc39b53477a2dcb9` and remains tracked.
   - Contains:
     - `SUPABASE_KEY=sb_publishable_slewOyII3s2T85VGBw77Zw_KGjV3V2J`
     - `SUPABASE_URL=https://your-project.supabase.co` (dummy URL)
     - `DATABASE_URL=postgresql://postgres:your_password@db.your_project.supabase.co:5432/postgres` (dummy URL)
2. **Hardcoded Fallback in Code**:
   - `config.py:19`: `SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_slewOyII3s2T85VGBw77Zw_KGjV3V2J")`
3. **Committed Bytecode**:
   - 14 compiled `.pyc` files in `__pycache__` directories were committed to git in commit `e511ed0`.
4. **Action Required**:
   - Remove `.env` and `__pycache__` from git tracking (`git rm --cached`).
   - Create `.gitignore` to prevent future commits of environment files and bytecode.
   - Note: The publishable key is tied to a dummy URL (`https://your-project.supabase.co`), so no live credentials were leaked to third-party endpoints. However, best practice requires removing hardcoded key strings.

---

## 7. PHASE 1F — Baseline Benchmark Record

The existing benchmark was executed on commit `3eaffd9` prior to any code or evaluation modifications.

- **Commit SHA**: `3eaffd917ca153ca347c89d42c1b5a0a4e2cb6e1`
- **Git Tag**: `baseline-v0`
- **Execution Date**: 2026-10-21T16:10:25Z
- **Command**: `python3 eval/evaluate.py`
- **Model**: None invoked (pure deterministic logic)
- **Dataset Count**: 24 ground-truth incident JSON files in `ground_truths/`
- **Raw Benchmark Output**:
  ```json
  {
    "total_incidents_evaluated": 24,
    "root_cause_accuracy_pct": 100.0,
    "retrieval_recall_pct": 100.0,
    "retrieval_precision_pct": 100.0,
    "false_confidence_rate_pct": 0.0,
    "avg_iterations_per_incident": 1.0,
    "avg_latency_seconds": 0.0,
    "timestamp": "2026-10-21T16:10:25.751784+00:00"
  }
  ```
- **Frozen File**: Saved in `eval/baseline_v0_raw.json`.

---

## 8. Summary of Claims That Must Change

1. **Remove "Autonomous SRE Agent"** $\rightarrow$ Reframe as **"Deterministic Workflow & Copilot for Incident Investigation"**.
2. **Remove "Zero AI Hallucination"** $\rightarrow$ Reframe as **"Evidence-Grounded Heuristic with Mandatory File/Line Citations"**.
3. **Remove "100% Retrieval Recall & Precision"** $\rightarrow$ Correctly report that vector RAG was not evaluated in baseline and measure actual evidence extraction against ground truth.
4. **Remove "Sub-second SLA"** $\rightarrow$ Report actual measured component latency (in-memory execution vs. LLM latency).
5. **Remove "Awwwards-Level UI"** $\rightarrow$ Use **"Linear-inspired dark observability console"**.
6. **Reframe "Deterministic Confidence Score"** $\rightarrow$ Reframe as **"Evidence Sufficiency Ratio (Laplace-smoothed Heuristic)"**, documenting the 3-item threshold clearly.

---

## 9. Summary of Code & Architecture Changes Required for Subsequent Phases

1. **Phase 2 (Evaluation Redesign)**:
   - Build 30–40 new evaluation cases with 6 distinct categories (including insufficient evidence, noisy logs, conflicting evidence, missing sources).
   - Separate development cases from a frozen holdout.
   - Define formal mathematical metrics in `EVALUATION.md`.
2. **Phase 3 (Explicit System States)**:
   - Expand status enum from `sufficient_confidence` / `insufficient_evidence` to explicit SRE states: `resolved`, `insufficient_evidence`, `unresolved_conflict`, `failed`, plus `degraded: bool`.
3. **Phase 4 (Citation Validation)**:
   - Build 3-level citation validator (Existence, Content Match, Semantic Support) with content hashing to detect code drift.
4. **Phase 5 (Structured Execution Traces)**:
   - Implement single structured trace per run capturing node timings, tool calls, token usage, and cost estimates. Build CLI benchmark runner (`python -m eval.run`).
5. **Phase 6 (Unit Tests)**:
   - Implement comprehensive pure unit tests for scoring, routing, and citation validation.
