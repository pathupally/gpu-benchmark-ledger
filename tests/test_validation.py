from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from benchmark_ledger.validation import validate_project


ROOT = Path(__file__).resolve().parents[1]


class ValidationTests(unittest.TestCase):
    def test_project_sources_are_valid(self) -> None:
        report = validate_project(ROOT)
        self.assertTrue(report["valid"], report["issues"])
        self.assertEqual(report["counts"]["observations"], 8)
        self.assertEqual(report["counts"]["pairs"], 4)

    def test_nonpositive_price_is_rejected_by_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "project"
            shutil.copytree(ROOT / "data" / "source", fixture / "data" / "source")
            shutil.copytree(ROOT / "schemas", fixture / "schemas")
            observations_path = fixture / "data" / "source" / "observations.jsonl"
            observations = [json.loads(line) for line in observations_path.read_text(encoding="utf-8").splitlines()]
            observations[0]["value"] = 0
            observations_path.write_text(
                "\n".join(json.dumps(row, separators=(",", ":")) for row in observations) + "\n",
                encoding="utf-8",
            )
            report = validate_project(fixture)
            self.assertFalse(report["valid"])
            self.assertIn("schema_exclusive_minimum", {issue["code"] for issue in report["issues"]})

    def test_approximate_pair_cannot_be_decision_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "project"
            shutil.copytree(ROOT / "data" / "source", fixture / "data" / "source")
            shutil.copytree(ROOT / "schemas", fixture / "schemas")
            pair_path = fixture / "data" / "source" / "benchmark-pairs.json"
            pair_book = json.loads(pair_path.read_text(encoding="utf-8"))
            approximate = next(pair for pair in pair_book["pairs"] if pair["comparison_class"] == "approximate")
            approximate["analysis_eligible"] = True
            pair_path.write_text(json.dumps(pair_book), encoding="utf-8")
            report = validate_project(fixture)
            self.assertFalse(report["valid"])
            self.assertIn("pair_approximate_eligible", {issue["code"] for issue in report["issues"]})


if __name__ == "__main__":
    unittest.main()

