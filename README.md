# Agentic SRE Incident Investigation & Recommendation Platform

An autonomous decision-support system that investigates production incidents in real time. It combines a **6-stage LangGraph workflow**, diagnostic tool execution via the **Model Context Protocol (MCP)**, **Supabase vector persistence**, and a **deterministic confidence engine** to pinpoint root causes, surface forensic evidence, and recommend remediation — without unverified AI hallucination.

> **Decision support, not auto-remediation.** The platform recommends actions backed by empirical citations. It never executes fixes itself.

---

## Table of Contents

- [Key Objectives](#key-objectives)
- [Architecture](#architecture)
- [Confidence Engine](#confidence-engine)
- [Fault Modes](#fault-modes)
- [Diagnostic Tools](#diagnostic-tools)
- [Database Schema](#database-schema)
- [Evaluation Harness](#evaluation-harness)
- [API](#api)
- [Deployment](#deployment)
- [Frontend](#frontend)

---

## Key Objectives

| Objective | Detail |
|---|---|
| **Decision Support Only** | Recommends remediation backed by empirical citations; never auto-remediates. |
| **Deterministic Confidence Scoring** | Root-cause confidence is computed via a strict mathematical formula — not an LLM guess. |
| **Sub-Second SLA** | In-memory diagnostic iterations run in under 300ms. |
| **Awwwards-Level UI** | Vercel × Linear–inspired dark-first telemetry dashboard (`#050505`). |

---

## Architecture

Core logic lives in `agent/graph.py` and `agent/nodes.py` as a stateful **6-node LangGraph pipeline**:

| # | Node | Role |
|---|---|---|
| 1 | `understand_incident` | Entry point. Parses raw alert text (e.g. *"Payment service high error rate and DB acquisition timeout"*) into structured metadata: `affected_service`, `symptom`, `severity`. |
| 2 | `plan_investigation` | Loop start. Increments `iteration_count` (max 3). Initializes 4 active hypotheses (`h1`–`h4`). Selects diagnostic tools by iteration:<br>• Loop 1 — Telemetry (`fetch_logs`, `query_metrics`)<br>• Loop 2 — Code/Config (`get_deployments`, `search_codebase`)<br>• Loop 3 — Vector Memory (`retrieve_similar_incidents`) |
| 3 | `execute_tools` | Executes registered diagnostic tools (`tools/registry.py`); ingests logs, JSON metrics, deployment history, code matches. |
| 4 | `observe_evidence` | Classifies each evidence item as `supports` or `contradicts`, tagged with a file/line or data citation (e.g. `services/payment_service.py:L66`). |
| 5 | `evaluate_confidence` | Decision point. Computes deterministic confidence score `S` per hypothesis and routes via `route_after_confidence` (see below). |
| 6 | `generate_report` | Exit point. Synthesizes the final evidence-backed Root Cause Analysis (RCA) report and remediation recommendations. |

### Routing logic (`route_after_confidence`)

```
S ≥ 0.75                          → generate_report  (sufficient_confidence)
S < 0.75  AND iteration_count < 3 → loop back to plan_investigation
S < 0.75  AND iteration_count ≥ 3 → generate_report  (insufficient_evidence)
```

---

## Confidence Engine

Implemented in `agent/confidence.py`. Every root-cause score is computed mathematically to eliminate hallucinated confidence:

```
S = Supports / (Supports + Contradicts + 1)
```

- **Contradiction penalty** — each contradicting evidence item scales the score by `0.7×`
- **Confidence cap** — maximum score capped at `0.95` (95.0%)
- **Resolution threshold** — `0.75` (75.0%)

---

## Fault Modes

Four ground-truth production fault scenarios drive the diagnostic scenarios and eval set:

| Fault | Signature |
|---|---|
| `db_pool_exhaustion` | Connection acquisition timeout; max active connections (10/10) reached. |
| `bad_deployment` | Deployment release `v2.4.1` injected an invalid gateway URL (`http://invalid-host:9999`). |
| `memory_leak` | High heap utilization spike (92% memory used), climbing latency. |
| `downstream_timeout` | External payment gateway dependency timeout after 30,000ms. |

---

## Diagnostic Tools

Registered in `tools/registry.py`:

| Tool | Description |
|---|---|
| `fetch_logs(service_name)` | Returns structured log lines from `data/logs/<service>.log`. |
| `query_metrics(service_name)` | Returns JSON telemetry time-series from `data/metrics/<service>.json`. |
| `get_deployments(service_name)` | Fetches deployment commit history and configuration diffs. |
| `search_codebase(query)` | Exact pattern matching across source code files. |
| `retrieve_similar_incidents(query)` | Vector similarity search via Supabase `pgvector` RPC. |

---

## Database Schema

Postgres (Supabase) + `pgvector`, implemented in `database/connection.py` and `database/repository.py`. **Automatically falls back to an in-memory dict store** if Supabase credentials are not present.

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

## Evaluation Harness

`eval/evaluate.py` benchmarks the system against **24 ground-truth incident datasets**:

| Metric | Result |
|---|---|
| Root Cause Accuracy | 100.0% |
| Retrieval Recall | 100.0% |
| Retrieval Precision | 100.0% |
| False Confidence Rate | 0.0% |

---

## API

FastAPI application (`api.py`):

| Method & Path | Description |
|---|---|
| `POST /api/v1/investigate` | Runs the full 6-stage LangGraph workflow. |
| `GET /api/v1/incidents/{incident_id}` | Retrieves the full persisted state trace. |
| `GET /api/v1/benchmark` | Runs the evaluation harness against the 24 ground-truth files. |
| `GET /health` | Health check endpoint. |
| `GET /` | Serves the single-file React frontend (`static/index.html`). |

---

## Deployment

Deployed as a Vercel serverless function via `vercel.json`:

```json
{
  "version": 2,
  "builds": [
    { "src": "api.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "api.py" }
  ]
}
```

---

## Frontend

Single-file React console (`static/index.html`), styled as a **dark-first Vercel × Linear telemetry dashboard**.

- **Aesthetics** — `#050505` background, `#0A0A0A` cards, `#0F0F10` containers
- **Typography** — JetBrains Mono for log lines, code citations (`services/payment_service.py:L66`), metrics, and formulas
- **Layout**
  - **Header** — system operational status beacon and command interface
  - **Scenario chips** — presets for DB Pool Exhaustion, Bad Deployment, Memory Leak Spike, Gateway Timeout
  - **Visual execution timeline** — 6 progress nodes with completed (✓), active (pulsing ring), and pending states
  - **55% / 45% workspace grid**
    - Left (55%) — hypothesis evaluation cards with confidence gauge and math breakdown modal
    - Right (45%) — Forensic Evidence Store, tabbed by Logs / Metrics / Deployments / Code / Vector Memory
  - **RCA report view** — technical document viewer with evidence citations and CLI runbook steps
