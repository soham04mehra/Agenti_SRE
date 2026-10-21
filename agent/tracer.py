import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Published list pricing for gpt-4o-mini (per 1,000 tokens)
PRICING_PER_1K_TOKENS = {
    "gpt-4o-mini": {
        "prompt": 0.00015,     # $0.15 per 1M tokens
        "completion": 0.00060  # $0.60 per 1M tokens
    }
}

class TraceSpan:
    def __init__(self, name: str, span_type: str = "node"):
        self.name = name
        self.span_type = span_type
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.metadata: Dict[str, Any] = {}

    def finish(self, **metadata):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.metadata.update(metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.span_type,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }

class ExecutionTracer:
    """Collects and computes unified structured execution metrics per investigation."""

    def __init__(self, incident_id: str, model_name: str = "gpt-4o-mini"):
        self.incident_id = incident_id
        self.model_name = model_name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.total_latency_ms: float = 0.0
        self.spans: List[TraceSpan] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.llm_calls: List[Dict[str, Any]] = []

    def start_span(self, name: str, span_type: str = "node") -> TraceSpan:
        span = TraceSpan(name, span_type)
        self.spans.append(span)
        return span

    def record_tool_call(self, tool_name: str, duration_ms: float, status: str, arguments: Optional[Dict[str, Any]] = None):
        self.tool_calls.append({
            "tool": tool_name,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "arguments": arguments or {}
        })

    def record_llm_call(self, prompt_tokens: int, completion_tokens: int, latency_ms: float):
        pricing = PRICING_PER_1K_TOKENS.get(self.model_name, PRICING_PER_1K_TOKENS["gpt-4o-mini"])
        cost = (prompt_tokens / 1000.0 * pricing["prompt"]) + (completion_tokens / 1000.0 * pricing["completion"])

        self.llm_calls.append({
            "model": self.model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": round(latency_ms, 2),
            "estimated_cost_usd": round(cost, 6),
            "pricing_source": "Published OpenAI list pricing"
        })

    def finish_trace(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        self.end_time = time.time()
        self.total_latency_ms = round((self.end_time - self.start_time) * 1000, 2)

        # Derived metrics
        node_latencies = {s.name: s.duration_ms for s in self.spans if s.span_type == "node"}
        total_tool_latency = sum(t["duration_ms"] for t in self.tool_calls)
        total_llm_latency = sum(l["latency_ms"] for l in self.llm_calls)
        total_cost = sum(l["estimated_cost_usd"] for l in self.llm_calls)
        total_tokens = sum(l["total_tokens"] for l in self.llm_calls)

        return {
            "incident_id": self.incident_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": final_state.get("status", "unknown"),
            "degraded": final_state.get("degraded", False),
            "confidence_score": final_state.get("confidence_score", 0.0),
            "iterations": final_state.get("iteration_count", 1),
            "latency": {
                "total_ms": self.total_latency_ms,
                "tool_ms": round(total_tool_latency, 2),
                "llm_ms": round(total_llm_latency, 2),
                "node_breakdown_ms": node_latencies
            },
            "costs": {
                "estimated_usd": round(total_cost, 6),
                "total_tokens": total_tokens,
                "label": "Estimated cost using published list pricing"
            },
            "spans": [s.to_dict() for s in self.spans],
            "tool_calls": self.tool_calls,
            "llm_calls": self.llm_calls
        }
