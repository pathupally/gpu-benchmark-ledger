from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from benchmark_ledger.pipeline import build, compute_analysis


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analysis = compute_analysis(ROOT)
        self.by_gpu = {pair["gpu_model"]: pair for pair in self.analysis["pairs"]}

    def test_documented_cross_section_is_reproduced(self) -> None:
        expected = {"H100": 10.6, "A100": -24.8, "B200": 7.7, "H200": 38.2}
        actual = {gpu: round(pair["basis"]["raw_pct"], 1) for gpu, pair in self.by_gpu.items()}
        self.assertEqual(actual, expected)
        self.assertTrue(self.analysis["headline"]["sign_reversal_present"])

    def test_nonrestated_break_ranges_are_carried_without_midpoints(self) -> None:
        h100 = self.by_gpu["H100"]["basis"]["break_sensitivity"]
        b200 = self.by_gpu["B200"]["basis"]["break_sensitivity"]
        self.assertEqual([event["event_id"] for event in h100["applied_breaks"]], ["sd-260325-1"])
        self.assertEqual([event["event_id"] for event in b200["applied_breaks"]], ["sd-260630-1"])
        self.assertAlmostEqual(h100["adjusted_pct_low"], 2.82641509)
        self.assertAlmostEqual(h100["adjusted_pct_high"], 7.2490566)
        self.assertAlmostEqual(b200["adjusted_pct_low"], 1.2437276)
        self.assertAlmostEqual(b200["adjusted_pct_high"], 7.70609319)
        self.assertIn("sd-251203-1", h100["restated_break_ids_excluded"])

    def test_unquantified_break_remains_visible(self) -> None:
        h100 = self.by_gpu["H100"]["basis"]["break_sensitivity"]
        self.assertFalse(h100["is_fully_bounded"])
        self.assertEqual(h100["status"], "partial_unbounded")
        self.assertEqual(h100["unquantified_break_ids"], ["sd-prose-2025-03-01"])

    def test_unsupported_estimates_have_no_numeric_result(self) -> None:
        for key in ("correlation", "rolling_hedge_ratio"):
            gate = self.analysis["analytics"][key]
            self.assertEqual(gate["status"], "unavailable")
            self.assertEqual(gate["observed_shared_levels"], 1)
            self.assertNotIn("value", gate)
        self.assertEqual(self.analysis["analytics"]["hedge_effectiveness"]["status"], "unavailable")

    def test_build_is_deterministic_and_writes_browser_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            build(ROOT, destination)
            dashboard = destination / "data" / "generated" / "dashboard.json"
            first = hashlib.sha256(dashboard.read_bytes()).hexdigest()
            build(ROOT, destination)
            second = hashlib.sha256(dashboard.read_bytes()).hexdigest()
            self.assertEqual(first, second)
            browser_payload = (destination / "web" / "data.generated.js").read_text(encoding="utf-8")
            self.assertTrue(browser_payload.startswith("window.BENCHMARK_LEDGER_DATA = "))
            self.assertIn('"sign_reversal_present":true', browser_payload)


if __name__ == "__main__":
    unittest.main()
