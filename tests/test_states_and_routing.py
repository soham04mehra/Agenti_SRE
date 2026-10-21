import unittest
from agent.nodes import evaluate_confidence_node, generate_report
from agent.graph import route_after_confidence
from database.repository import normalize_status

class TestStatesAndRouting(unittest.TestCase):

    def test_resolved_state_transition(self):
        """Sufficient evidence (>= 0.75) with no contradictions transitions to 'resolved'."""
        state = {
            "hypotheses": [
                {"id": "h1", "title": "DB Pool Exhaustion", "confidence_score": 0.0}
            ],
            "evidence": [
                {"hypothesis_id": "h1", "classification": "supports"},
                {"hypothesis_id": "h1", "classification": "supports"},
                {"hypothesis_id": "h1", "classification": "supports"}
            ],
            "iteration_count": 1,
            "max_iterations": 3,
            "degraded": False,
            "raw_data_refs": []
        }
        res = evaluate_confidence_node(state)
        self.assertEqual(res["status"], "resolved")
        self.assertGreaterEqual(res["confidence_score"], 0.75)
        self.assertFalse(res["degraded"])

    def test_insufficient_evidence_at_max_iterations(self):
        """Low confidence at max iterations transitions to 'insufficient_evidence'."""
        state = {
            "hypotheses": [
                {"id": "h1", "title": "DB Pool Exhaustion", "confidence_score": 0.0}
            ],
            "evidence": [],
            "iteration_count": 3,
            "max_iterations": 3,
            "degraded": False,
            "raw_data_refs": []
        }
        res = evaluate_confidence_node(state)
        self.assertEqual(res["status"], "insufficient_evidence")
        self.assertLess(res["confidence_score"], 0.75)

    def test_investigating_before_max_iterations(self):
        """Low confidence before max iterations remains in 'investigating'."""
        state = {
            "hypotheses": [
                {"id": "h1", "title": "DB Pool Exhaustion", "confidence_score": 0.0}
            ],
            "evidence": [],
            "iteration_count": 1,
            "max_iterations": 3,
            "degraded": False,
            "raw_data_refs": []
        }
        res = evaluate_confidence_node(state)
        self.assertEqual(res["status"], "investigating")

    def test_unresolved_conflict_transition(self):
        """Unresolved contradiction on top hypothesis at max iterations transitions to 'unresolved_conflict'."""
        state = {
            "hypotheses": [
                {"id": "h1", "title": "DB Pool Exhaustion", "confidence_score": 0.0}
            ],
            "evidence": [
                {"hypothesis_id": "h1", "classification": "supports"},
                {"hypothesis_id": "h1", "classification": "contradicts"}
            ],
            "iteration_count": 3,
            "max_iterations": 3,
            "degraded": False,
            "raw_data_refs": []
        }
        res = evaluate_confidence_node(state)
        self.assertEqual(res["status"], "unresolved_conflict")

    def test_failed_state_transition(self):
        """Systemic tool failure sets status to 'failed' and degraded to True."""
        state = {
            "hypotheses": [{"id": "h1", "title": "Test", "confidence_score": 0.0}],
            "evidence": [],
            "iteration_count": 1,
            "max_iterations": 3,
            "degraded": False,
            "raw_data_refs": [
                {"tool": "fetch_logs", "output": {"status": "error"}},
                {"tool": "query_metrics", "output": {"status": "error"}}
            ]
        }
        res = evaluate_confidence_node(state)
        self.assertEqual(res["status"], "failed")
        self.assertTrue(res["degraded"])

    def test_router_deterministic_transitions(self):
        """route_after_confidence routes terminal states to generate_report and investigating to replan."""
        self.assertEqual(route_after_confidence({"status": "resolved"}), "generate_report")
        self.assertEqual(route_after_confidence({"status": "insufficient_evidence"}), "generate_report")
        self.assertEqual(route_after_confidence({"status": "unresolved_conflict"}), "generate_report")
        self.assertEqual(route_after_confidence({"status": "failed"}), "generate_report")
        # Legacy status backward compatibility
        self.assertEqual(route_after_confidence({"status": "sufficient_confidence"}), "generate_report")
        # Loop back
        self.assertEqual(route_after_confidence({"status": "investigating"}), "replan")

    def test_backward_compatibility_normalization(self):
        """normalize_status converts legacy 'sufficient_confidence' to 'resolved'."""
        self.assertEqual(normalize_status("sufficient_confidence"), "resolved")
        self.assertEqual(normalize_status("insufficient_evidence"), "insufficient_evidence")
        self.assertEqual(normalize_status("unresolved_conflict"), "unresolved_conflict")
        self.assertEqual(normalize_status("resolved"), "resolved")
        self.assertEqual(normalize_status(None), "investigating")

    def test_report_generation_for_conflict_and_failure(self):
        """generate_report produces valid schema for unresolved_conflict and failed."""
        conflict_state = {
            "status": "unresolved_conflict",
            "confidence_score": 0.35,
            "hypotheses": [{"id": "h1", "title": "DB Pool", "confidence_score": 0.35}],
            "evidence": [{"hypothesis_id": "h1", "classification": "contradicts", "summary": "test"}],
            "degraded": False
        }
        rep = generate_report(conflict_state)
        self.assertEqual(rep["final_report"]["status"], "UNRESOLVED_CONFLICT")
        self.assertIn("conflicting_evidence", rep["final_report"])

        failed_state = {
            "status": "failed",
            "confidence_score": 0.0,
            "hypotheses": [],
            "evidence": [],
            "degraded": True
        }
        rep_failed = generate_report(failed_state)
        self.assertEqual(rep_failed["final_report"]["status"], "FAILED")
        self.assertTrue(rep_failed["final_report"]["degraded"])

if __name__ == "__main__":
    unittest.main()
