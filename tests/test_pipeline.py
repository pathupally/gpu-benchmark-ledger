from __future__ import annotations

import hashlib
import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from benchmark_ledger.analytics import cross_benchmark_tracking
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
            self.assertEqual(gate["levels_required"], 61)
            self.assertNotIn("value", gate)
        self.assertEqual(self.analysis["analytics"]["hedge_effectiveness"]["status"], "unavailable")

    def test_strict_basis_monitor_rejects_unknown_or_mismatched_dimensions(self) -> None:
        monitor = self.analysis["basis_monitor"]
        self.assertEqual(monitor["status"], "unavailable")
        self.assertEqual(monitor["candidate_pairs"], 4)
        self.assertEqual(monitor["admitted_pairs"], 0)
        self.assertEqual(monitor["required_count"], 120)
        excluded = {row["pair_id"]: row["reasons"] for row in monitor["exclusions"]}
        self.assertIn("tier_unknown", excluded["pair-h200-2026-08-29"])
        self.assertIn("rental_type_mismatch", excluded["pair-b200-2026-08-29"])

    @staticmethod
    def _synthetic_tracking_levels(count: int = 81) -> tuple[list[str], list[float], list[float]]:
        dates = [(date(2026, 1, 1) + timedelta(days=index)).isoformat() for index in range(count)]
        sd = [80.0]
        ornn = [100.0]
        pattern = [0.01, -0.006, 0.014, -0.009, 0.004]
        for index in range(1, count):
            tracker_return = pattern[(index - 1) % len(pattern)]
            ornn.append(ornn[-1] * math.exp(tracker_return))
            sd.append(sd[-1] * math.exp(1.75 * tracker_return))
        return dates, sd, ornn

    def test_tracking_estimator_is_gated_below_61_levels(self) -> None:
        dates, sd, ornn = self._synthetic_tracking_levels(60)
        result = cross_benchmark_tracking(dates, sd, ornn)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["observed_count"], 60)
        self.assertEqual(result["required_count"], 61)
        self.assertNotIn("variance_reduction", result)

    def test_tracking_estimator_recovers_known_beta(self) -> None:
        dates, sd, ornn = self._synthetic_tracking_levels()
        result = cross_benchmark_tracking(dates, sd, ornn)
        self.assertEqual(result["status"], "available")
        self.assertGreater(result["out_of_sample_returns"], 2)
        self.assertTrue(all(abs(row["beta"] - 1.75) < 1e-7 for row in result["evaluations"]))
        self.assertAlmostEqual(result["variance_reduction"], 1.0, places=7)

    def test_tracking_coefficient_does_not_look_ahead(self) -> None:
        dates, sd, ornn = self._synthetic_tracking_levels()
        baseline = cross_benchmark_tracking(dates, sd, ornn)
        shocked = list(ornn)
        shocked[-1] *= 4
        with_shock = cross_benchmark_tracking(dates, sd, shocked)
        self.assertEqual(
            baseline["evaluations"][-1]["beta"],
            with_shock["evaluations"][-1]["beta"],
        )
        self.assertLess(
            baseline["evaluations"][-1]["training_end"],
            baseline["evaluations"][-1]["date"],
        )

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
