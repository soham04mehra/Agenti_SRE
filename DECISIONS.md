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
