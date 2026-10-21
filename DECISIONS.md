# DECISIONS.md — Engineering Architecture & Evaluation Log

This document records architectural, evaluation, and system design decisions made during the audit and hardening of the Agentic SRE Platform.

---

### Record 001: Branch Isolation & Baseline Tagging for Audit

- **Decision**: Create an isolated git branch (`audit-and-hardening`) and tag the pre-audit commit `3eaffd9` as `baseline-v0`.
- **Why**: Rule 1 and Rule 7 require protecting the live deployment (`https://agenti-sre.vercel.app`) and strictly preserving the baseline evaluation state without retroactive changes.
- **Alternatives considered**:
  1. Auditing directly on `main`: Rejected because any change could trigger unintended production redeployments or break live endpoint stability.
  2. Forking to a separate repository: Rejected because it breaks commit lineage and makes comparing baseline vs. hardened evaluations difficult.
- **Why this approach was selected**: Git branch isolation (`audit-and-hardening`) ensures zero impact on production, while `baseline-v0` creates an immutable historical anchor for benchmark scores.
- **Tradeoffs**: Requires maintaining branch hygiene and deliberate merging only after validation.

---

### Record 002: Baseline Benchmark Output Preservation

- **Decision**: Save the exact raw JSON output of `eval/evaluate.py` at commit `3eaffd9` as `eval/baseline_v0_raw.json` without modifying any logic.
- **Why**: Rule 4 and Rule 5 mandate preserving baseline measurements exactly as measured, documenting flaws rather than quietly patching them before the baseline is recorded.
- **Alternatives considered**:
  1. Fixing Node 4 shortcut before taking baseline: Rejected because it would falsify historical project performance.
  2. Omitting baseline recording: Rejected because engineering credibility requires showing the evolution from baseline to hardened system.
- **Why this approach was selected**: A frozen baseline provides empirical evidence of the system's actual behavior before hardening.
- **Tradeoffs**: The baseline clearly documents that the initial "100% accuracy / 0.0s latency" resulted from static keyword matching rather than real agentic reasoning.

---

### Record 003: Robustness Evaluation Suite & Frozen Holdout Partitioning

- **Decision**: Expand evaluation from 24 synthetic single-fault cases to a 36-case robustness benchmark partitioned into an 18-case development set (`eval/datasets/dev/`) and an 18-case frozen holdout set (`eval/datasets/holdout/`), tagged as `holdout-v1`.
- **Why**: Rule 3 and Phase 2 require testing the system on difficult real-world failure modes (insufficient evidence, noisy logs, conflicting telemetry, red herrings, missing diagnostic sources) while preventing data leakage and overfitting.
- **Alternatives considered**:
  1. Evaluating solely on the original 24 ground-truth cases: Rejected because it leaves the system vulnerable to accusations of memorization and gives a false 100% confidence signal.
  2. Running benchmarks without a holdout split: Rejected because tuning directly against the test set invalidates evaluation rigor.
  3. LLM-generated dynamic cases at runtime: Rejected for holdout because reproducibility requires an immutable, frozen dataset with deterministic grading.
- **Why this approach was selected**: Equal distribution across 6 categories (3 dev / 3 holdout each) provides sufficient sample size to evaluate both definitive diagnosis and abstention safety, with zero holdout contamination.
- **Tradeoffs**: Decreases reported benchmark percentages initially (from 100% down to 0% RCA / 66.7% CAR on the unhardened system), but provides an authentic, defensible foundation.

---

### Record 004: Explicit SRE State Machine, Contradiction Routing & Degraded Observability

- **Decision**: Refactor the status schema from a binary outcome (`sufficient_confidence` / `insufficient_evidence`) into four explicit SRE terminal states (`resolved`, `insufficient_evidence`, `unresolved_conflict`, `failed`) and add a `degraded: bool` observability flag.
- **Why**: Phase 3 requires the system to handle real-world uncertainty safely. A system must distinguish between "insufficient data" (need more signals), "unresolved conflict" (contradictory metrics), "failed" (infrastructure/tool errors), and "degraded" (missing metric snapshots).
- **Alternatives considered**:
  1. Letting the LLM generate status strings dynamically: Rejected because it violates deterministic state machine guarantees and allows hallucinated statuses.
  2. Sticking with binary status and relying solely on confidence thresholds: Rejected because a threshold cannot distinguish between conflicting evidence (active contradictions) and absent evidence (0 data).
  3. Breaking changes to old DB records: Rejected in favor of an explicit normalizer (`normalize_status`) that maps legacy `sufficient_confidence` to `resolved` on read.
- **Why this approach was selected**: Provides deterministic routing in LangGraph, backward compatibility for database and API clients, and explicit observability into degraded diagnostic sources.
- **Tradeoffs**: Requires maintaining report schemas for four distinct terminal outcomes rather than two.

---

### Record 005: 3-Level Cryptographic Citation Validation & Drift Detection

- **Decision**: Implement a 3-level citation validator (`CitationValidator` in `agent/citation.py`) with SHA-256 snippet hashing for source code drift detection.
- **Why**: Phase 4 requires evidence claims to be verifiable. In production, code and logs drift over time; static file and line references (`L66`) break when commits modify files. Storing a cryptographic hash of the evidence snippet alongside the source and line bounds ensures that citations are tamper-evident and immune to silent drift.
- **Alternatives considered**:
  1. Relying exclusively on line numbers: Rejected because any line insertion or deletion immediately breaks the reference.
  2. Relying on an LLM to judge every citation: Rejected because it introduces latency, stochasticity, and token costs for what should be deterministic existence and substring checks.
- **Why this approach was selected**: 3-level deterministic hierarchy (Level 1: Existence, Level 2: Content Match & Hash Drift, Level 3: Semantic Grounding) executes in sub-millisecond time while catching broken paths, out-of-bound lines, and drifted snippets.
- **Tradeoffs**: Requires creating structured citation records with normalized snippets rather than free-form string URLs.

---

### Record 006: Diagnostic Telemetry Parsing, Source Grounding & Execution Tracing

- **Decision**: Replace the Node 4 (`observe_evidence`) substring shortcut with deterministic telemetry parsing over actual tool outputs (`raw_data_refs` containing logs, metrics, deployments, code search results). Integrate `ExecutionTracer` in `agent/tracer.py` to record per-node spans, tool latencies, token counters, and API list-price costs.
- **Why**: Phase 5 requires that evidence grounding and hypothesis scoring depend on diagnostic findings returned by tools, not the human incident prompt. The original Node 4 relied on matching substrings in `state["raw_description"]`, causing a 33.3% false-confidence rate on conflicting cases and complete failure when real phrasing differed from synthetic template strings.
- **Alternatives considered**:
  1. Passing all raw tool outputs to an LLM node for unstructured evidence extraction: Rejected because it introduces 2-5 seconds of latency per loop, potential hallucinations, stochastic evidence counts, and unnecessary token costs.
  2. Bypassing tool outputs and keeping description regex: Rejected because it is not an agentic SRE system; it is a toy keyword classifier.
- **Why this approach was selected**: Telemetry parsing directly inspects tool outputs (e.g., active database connection gauges, error rates, warning logs, git deployment metadata), extracts verbatim snippets for cryptographic citations, and cleanly flags conflicting evidence (e.g. latency spike without DB pool pressure) and missing diagnostic sources.
- **Tradeoffs**: Diagnostic tool outputs must adhere to standardized structured payloads (`logs`, `metrics`, `deployments`, `code_results`).

---

### Record 007: Pure Logic Unit Testing for Confidence, Router Transitions, and Execution Tracing

- **Decision**: Add isolated unit tests (`tests/test_confidence_and_tracing.py`) validating the mathematical boundaries of the confidence formula $S / (S + C + 1)$, contradiction penalties, ceiling caps (0.95), ranking logic, and execution tracer cost calculations.
- **Why**: Tier 1 requirement 10 mandates that all pure deterministic logic must be validated with isolated unit tests without network calls, LLM dependencies, or mock flakiness.
- **Alternatives considered**:
  1. Relying exclusively on end-to-end benchmark integration runs: Rejected because end-to-end tests obscure boundary edge cases (e.g. exactly 3 supporting items hitting 0.75 vs 2 items hitting 0.67).
  2. Mocking LangGraph runtime: Rejected in favor of directly testing pure functions (`calculate_confidence`, `route_after_confidence`, `normalize_status`, `finish_trace`).
- **Why this approach was selected**: High speed (< 2ms total execution for 24 tests), zero dependencies, and deterministic validation of mathematical properties and state machine rules.
- **Tradeoffs**: None. Pure unit tests maintain local developer velocity.

---

### Record 008: Evidence Modality Classification & Source Grouping

- **Decision**: Extend `CitationRecord` with deterministic source modality inference (`infer_source_type`: `logs`, `metrics`, `deployments`, `codebase`) and source grouping (`group_by_source_type`). Include source-grouped evidence breakdown in the final report payload.
- **Why**: Phase 7 (Tier 2 requirement 1) requires evidence to be structured by diagnostic modality. In SRE root-cause investigations, a critical interview challenge is: "What stops 10 duplicate log lines from inflating your confidence score to 95%?" Deduplication by summary/snippet combined with modality grouping proves that an RCA is corroborated across independent diagnostic sources (e.g., metric spikes + error logs + deployment diffs) rather than repetitive log spam.
- **Alternatives considered**:
  1. Letting the LLM classify evidence types: Rejected as non-deterministic, slow, and prone to hallucinations.
  2. Freeform citation strings without modality tagging: Rejected because downstream consumers (UI, SRE alert aggregators) cannot group evidence by source.
- **Why this approach was selected**: Clean, sub-millisecond regex/path classification that maps citations directly to observability silos.
- **Tradeoffs**: Citations must adhere to known path conventions or default to the `other`/`telemetry` category.

---

### Record 009: Failure Mode Cataloging & Post-Mortem Documentation

- **Decision**: Publish `FAILURE_ANALYSIS.md` cataloging the six root vulnerabilities uncovered during repository auditing (Node 4 prompt shortcut, cross-incident telemetry bleed, warning log filtering, citation drift, binary state limitations, uncalibrated confidence claims).
- **Why**: SRE and GenAI hiring evaluations demand technical defensibility. Presenting a sanitized project with no documented failure modes reads as junior or artificial. Documenting actual failures, root causes, and architectural remedies demonstrates senior engineering rigor.
- **Alternatives considered**:
  1. Hiding past flaws: Rejected because an audit specifically aims to expose and resolve technical vulnerabilities.
  2. Generic failure writeup: Rejected in favor of exact file paths, line references, and measured performance deltas (e.g., 0% vs 100% RCA).
- **Why this approach was selected**: Establishes transparent accountability and provides a direct reference for technical interviews.
- **Tradeoffs**: None. Increases project documentation depth.

---

### Record 010: SRE Observability UI Hardening & Evidence Sufficiency Framing

- **Decision**: Update `static/index.html` to replace the binary "RESOLVED" badge and uncalibrated "100% confidence" label with:
  1. 4 explicit status badges (`RESOLVED`, `INSUFFICIENT EVIDENCE`, `UNRESOLVED CONFLICT`, `INVESTIGATION FAILED`) plus `DEGRADED` telemetry indicator.
  2. Modality filter tabs (`logs`, `metrics`, `codebase`, `deployments`) and cryptographic SHA-256 snippet hash displays.
  3. Relabeling "Confidence" to "Evidence Sufficiency Score" with explicit mathematical documentation of the $S / (S + C + 1)$ heuristic.
  4. Benchmark presentation showing exact fractions ($6/6$ RCA, $12/12$ CAR, $0/12$ FCR) across the 36-case robustness suite.
- **Why**: Phase 9 (Tier 2 requirement 4) and interview readiness require the frontend presentation to reflect technical reality rather than marketing hype. A Senior SRE expects to see why an investigation abstained or flagged contradictory signals.
- **Alternatives considered**:
  1. Complete frontend rewrite in Next.js: Rejected because it violates Rule 8 (unnecessary rewrite/dependencies) and risks breaking Vercel static serving.
  2. Leaving UI unchanged: Rejected because the UI previously hardcoded "RESOLVED" and claimed uncalibrated 100% certainty.
- **Why this approach was selected**: Preserves lightweight, zero-build React 18 single-file architecture while providing engineering-grade SRE observability.
- **Tradeoffs**: Relies on browser-side React 18 CDN for zero-build execution.




