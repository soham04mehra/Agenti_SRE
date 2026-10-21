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
