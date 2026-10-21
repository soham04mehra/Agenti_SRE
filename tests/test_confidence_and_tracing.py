import unittest
from agent.confidence import calculate_confidence, evaluate_all_hypotheses
from agent.tracer import ExecutionTracer, TraceSpan

class TestConfidenceAndTracing(unittest.TestCase):

    def test_confidence_zero_evidence(self):
        """Zero evidence yields 0.0 confidence."""
        hypo = {"id": "db_pool_exhaustion"}
        score = calculate_confidence(hypo, [])
        self.assertEqual(score, 0.0)

    def test_confidence_supports_progression(self):
        """
        Verify exact formula progression S / (S + C + 1):
        1 support -> 1 / (1 + 0 + 1) = 0.50
        2 supports -> 2 / (2 + 0 + 1) = 0.67
        3 supports -> 3 / (3 + 0 + 1) = 0.75 (Exact threshold boundary)
        4 supports -> 4 / (4 + 0 + 1) = 0.80
        """
        hypo = {"id": "bad_deployment"}
        
        ev_1 = [{"hypothesis_id": "bad_deployment", "classification": "supports"}]
        self.assertEqual(calculate_confidence(hypo, ev_1), 0.50)

        ev_2 = ev_1 + [{"hypothesis_id": "bad_deployment", "classification": "supports"}]
        self.assertEqual(calculate_confidence(hypo, ev_2), 0.67)

        ev_3 = ev_2 + [{"hypothesis_id": "bad_deployment", "classification": "supports"}]
        self.assertEqual(calculate_confidence(hypo, ev_3), 0.75)

        ev_4 = ev_3 + [{"hypothesis_id": "bad_deployment", "classification": "supports"}]
        self.assertEqual(calculate_confidence(hypo, ev_4), 0.80)

    def test_confidence_contradiction_penalty(self):
        """
        Contradictions apply a 0.7x penalty factor:
        3 supports + 1 contradiction:
        Base = 3 / (3 + 1 + 1) = 0.60
        With 0.7x penalty = 0.60 * 0.7 = 0.42
        """
        hypo = {"id": "memory_leak"}
        evidence = [
            {"hypothesis_id": "memory_leak", "classification": "supports"},
            {"hypothesis_id": "memory_leak", "classification": "supports"},
            {"hypothesis_id": "memory_leak", "classification": "supports"},
            {"hypothesis_id": "memory_leak", "classification": "contradicts"}
        ]
        self.assertEqual(calculate_confidence(hypo, evidence), 0.42)

    def test_confidence_max_cap(self):
        """Confidence score cannot exceed 0.95 cap regardless of evidence volume."""
        hypo = {"id": "downstream_timeout"}
        massive_evidence = [{"hypothesis_id": "downstream_timeout", "classification": "supports"} for _ in range(50)]
        score = calculate_confidence(hypo, massive_evidence)
        self.assertEqual(score, 0.95)

    def test_evaluate_all_hypotheses_selection(self):
        """evaluate_all_hypotheses ranks and selects the highest scoring hypothesis."""
        hypotheses = [
            {"id": "h1", "title": "DB Pool"},
            {"id": "h2", "title": "Memory Leak"}
        ]
        evidence = [
            {"hypothesis_id": "h2", "classification": "supports"},
            {"hypothesis_id": "h2", "classification": "supports"}
        ]
        best_score, top = evaluate_all_hypotheses(hypotheses, evidence)
        self.assertEqual(top["id"], "h2")
        self.assertEqual(best_score, 0.67)
        self.assertEqual(hypotheses[0]["confidence_score"], 0.0)
        self.assertEqual(hypotheses[1]["confidence_score"], 0.67)

    def test_tracer_span_and_tool_call(self):
        """ExecutionTracer records spans, tool calls, and calculates latencies."""
        tracer = ExecutionTracer(incident_id="inc_test_123", model_name="gpt-4o-mini")
        
        span = tracer.start_span("retrieve_telemetry", span_type="node")
        span.finish(node_name="retrieve_telemetry")
        
        tracer.record_tool_call("fetch_logs", duration_ms=12.5, status="success", arguments={"lines": 100})
        
        final_state = {"status": "resolved", "confidence_score": 0.8, "iteration_count": 1}
        trace_data = tracer.finish_trace(final_state)

        self.assertEqual(trace_data["incident_id"], "inc_test_123")
        self.assertEqual(trace_data["status"], "resolved")
        self.assertEqual(len(trace_data["spans"]), 1)
        self.assertEqual(len(trace_data["tool_calls"]), 1)
        self.assertEqual(trace_data["tool_calls"][0]["tool"], "fetch_logs")
        self.assertEqual(trace_data["latency"]["tool_ms"], 12.5)

    def test_tracer_cost_computation(self):
        """Tracer computes API costs accurately according to published list pricing."""
        tracer = ExecutionTracer(incident_id="inc_cost_test", model_name="gpt-4o-mini")
        # 1000 prompt tokens ($0.15/1M) = $0.00015
        # 500 completion tokens ($0.60/1M) = $0.00030
        # Total = $0.00045
        tracer.record_llm_call(prompt_tokens=1000, completion_tokens=500, latency_ms=250.0)
        
        final_state = {"status": "resolved"}
        trace = tracer.finish_trace(final_state)
        
        self.assertEqual(trace["costs"]["total_tokens"], 1500)
        self.assertAlmostEqual(trace["costs"]["estimated_usd"], 0.00045, places=5)
        self.assertEqual(trace["llm_calls"][0]["model"], "gpt-4o-mini")

    def test_get_supported_hypotheses_multi_cause(self):
        """get_supported_hypotheses extracts all hypotheses meeting or exceeding threshold."""
        from agent.confidence import get_supported_hypotheses
        hypos = [
            {"id": "h1", "title": "DB Pool", "confidence_score": 0.80},
            {"id": "h2", "title": "Bad Deployment", "confidence_score": 0.75},
            {"id": "h3", "title": "Memory Leak", "confidence_score": 0.50}
        ]
        supported = get_supported_hypotheses(hypos, threshold=0.75)
        self.assertEqual(len(supported), 2)
        self.assertEqual(supported[0]["id"], "h1")
        self.assertEqual(supported[1]["id"], "h2")

    def test_generate_report_multi_cause(self):
        """generate_report detects concurrent root causes and formats report accordingly."""
        from agent.nodes import generate_report
        state = {
            "status": "resolved",
            "confidence_score": 0.80,
            "hypotheses": [
                {"id": "db_pool_exhaustion", "title": "DB Pool", "confidence_score": 0.80},
                {"id": "bad_deployment", "title": "Bad Deployment", "confidence_score": 0.75}
            ],
            "evidence": [
                {"classification": "supports", "source": "data/logs/payment_service.log", "summary": "DB pool saturated"},
                {"classification": "supports", "source": "deployments/payment_service/v1.2.4", "summary": "Config error"}
            ],
            "degraded": False
        }
        res = generate_report(state)
        report = res["final_report"]
        self.assertTrue(report["is_multi_cause"])
        self.assertEqual(len(report["confirmed_root_causes"]), 2)
        self.assertIn("db_pool_exhaustion", report["confirmed_root_causes"])
        self.assertIn("bad_deployment", report["confirmed_root_causes"])

if __name__ == "__main__":
    unittest.main()
