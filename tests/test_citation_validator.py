import unittest
from pathlib import Path
from agent.citation import CitationValidator, CitationRecord

BASE_DIR = Path(__file__).resolve().parent.parent

class TestCitationValidator(unittest.TestCase):

    def setUp(self):
        self.validator = CitationValidator(base_dir=BASE_DIR)

    def test_level_1_missing_file(self):
        """Level 1 fails when referenced file path does not exist."""
        citation = {
            "source": "non_existent_dir/fake_logs.log",
            "summary": "Fake log line"
        }
        passed, msg = self.validator.validate_level_1_existence(citation)
        self.assertFalse(passed)
        self.assertIn("does not exist", msg)

    def test_level_1_valid_file_and_line(self):
        """Level 1 passes when file exists and line is within bounds."""
        citation = {
            "source": "services/payment_service.py",
            "line_start": 66,
            "summary": "DB pool error line"
        }
        passed, msg = self.validator.validate_level_1_existence(citation)
        self.assertTrue(passed)

    def test_level_1_invalid_line_number(self):
        """Level 1 fails when line number exceeds total file lines."""
        citation = {
            "source": "services/payment_service.py",
            "line_start": 99999,
            "summary": "Out of bounds line"
        }
        passed, msg = self.validator.validate_level_1_existence(citation)
        self.assertFalse(passed)
        self.assertIn("out of bounds", msg)

    def test_level_2_content_match_success(self):
        """Level 2 passes when snippet matches actual file content."""
        citation = {
            "source": "services/payment_service.py",
            "line_start": 76,
            "snippet": "max_connections=10 reached, connection acquisition timed out"
        }
        passed, msg = self.validator.validate_level_2_content_match(citation)
        self.assertTrue(passed)

    def test_level_2_content_mismatch_fails(self):
        """Level 2 fails when snippet content does not match referenced line."""
        citation = {
            "source": "services/payment_service.py",
            "line_start": 76,
            "snippet": "Kubernetes pod evicted due to disk pressure"
        }
        passed, msg = self.validator.validate_level_2_content_match(citation)
        self.assertFalse(passed)

    def test_level_2_drift_detection(self):
        """Level 2 detects drift when stored snippet_hash does not match modified content."""
        citation = {
            "source": "services/payment_service.py",
            "line_start": 76,
            "snippet": '"DB pool exhausted: max_connections=10 reached, connection acquisition timed out",',
            "snippet_hash": "deadbeef12345678"  # Stale hash simulating code drift
        }
        passed, msg = self.validator.validate_level_2_content_match(citation)
        self.assertFalse(passed)
        self.assertIn("drift detected", msg)

    def test_level_3_semantic_support_success(self):
        """Level 3 passes when evidence corroborates hypothesis fault pattern."""
        citation = {
            "snippet": "DB pool exhausted: max_connections=10 reached",
            "classification": "supports"
        }
        hypothesis = {"id": "db_pool_exhaustion"}
        passed, msg = self.validator.validate_level_3_semantic_support(citation, hypothesis)
        self.assertTrue(passed)

    def test_level_3_semantic_support_mismatch(self):
        """Level 3 fails when evidence does not match hypothesis fault keywords."""
        citation = {
            "snippet": "Payment gateway URL configuration invalid endpoint",
            "classification": "supports"
        }
        hypothesis = {"id": "db_pool_exhaustion"}
        passed, msg = self.validator.validate_level_3_semantic_support(citation, hypothesis)
        self.assertFalse(passed)

    def test_validate_all_aggregation(self):
        """validate_all aggregates levels 1, 2, and 3 into comprehensive report."""
        citation = CitationRecord.create_citation(
            source="services/payment_service.py",
            snippet="DB pool exhausted: max_connections=10 reached",
            classification="supports",
            hypothesis_id="db_pool_exhaustion",
            summary="DB pool error at line 76",
            line_start=76
        )
        report = self.validator.validate_all(citation)
        self.assertTrue(report["valid"])
        self.assertTrue(report["level_1_existence"]["passed"])
        self.assertTrue(report["level_2_content"]["passed"])
        self.assertTrue(report["level_3_semantic"]["passed"])

    def test_infer_source_type(self):
        """CitationRecord accurately classifies source modalities."""
        self.assertEqual(CitationRecord.infer_source_type("data/logs/payment_service.log"), "logs")
        self.assertEqual(CitationRecord.infer_source_type("data/metrics/payment_service.json"), "metrics")
        self.assertEqual(CitationRecord.infer_source_type("deployments/payment_service/v1.2.4"), "deployments")
        self.assertEqual(CitationRecord.infer_source_type("services/payment_service.py"), "codebase")

    def test_group_by_source_type(self):
        """group_by_source_type clusters citations by their modality."""
        ev = [
            CitationRecord.create_citation("data/logs/app.log", "error", "supports", "h1", "log ev"),
            CitationRecord.create_citation("data/metrics/app.json", "err=1", "supports", "h1", "metric ev"),
            CitationRecord.create_citation("services/app.py", "def pay():", "supports", "h1", "code ev")
        ]
        groups = CitationRecord.group_by_source_type(ev)
        self.assertEqual(len(groups["logs"]), 1)
        self.assertEqual(len(groups["metrics"]), 1)
        self.assertEqual(len(groups["codebase"]), 1)
        self.assertEqual(len(groups["deployments"]), 0)

if __name__ == "__main__":
    unittest.main()
