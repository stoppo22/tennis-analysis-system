import unittest

import numpy as np

from benchmark.evaluate_events import evaluate_events
from benchmark.bootstrap import (
    bootstrap_metrics,
    count_events_by_block,
    merge_counts,
    metrics_from_totals,
    paired_bootstrap_difference,
)


class CountEventsByBlockTest(unittest.TestCase):
    def test_attributes_events_to_the_right_blocks(self):
        counts = count_events_by_block(
            "clip",
            ground_truth_times=[1.0, 12.0],
            predicted_times=[1.1, 25.0],
            block_seconds=10.0,
        )

        self.assertEqual(counts[("clip", 0)], (1, 0, 0))  # matched at 1.0 s
        self.assertEqual(counts[("clip", 1)], (0, 0, 1))  # missed at 12.0 s
        self.assertEqual(counts[("clip", 2)], (0, 1, 0))  # false positive 25 s

    def test_totals_equal_evaluate_events_counts(self):
        ground_truth = [1.0, 2.0, 3.0, 14.0]
        predictions = [0.9, 1.0, 3.05, 40.0]
        counts = count_events_by_block(
            "clip",
            ground_truth_times=ground_truth,
            predicted_times=predictions,
            block_seconds=5.0,
        )
        totals = np.array(list(counts.values())).sum(axis=0)
        metrics = evaluate_events(ground_truth, predictions)

        self.assertEqual(
            totals.tolist(),
            [
                metrics["true_positives"],
                metrics["false_positives"],
                metrics["false_negatives"],
            ],
        )
        self.assertEqual(totals.tolist(), [2, 2, 2])

    def test_whole_clip_block(self):
        counts = count_events_by_block(
            "clip", [1.0, 50.0], [1.0], block_seconds=None
        )

        self.assertEqual(counts, {("clip", 0): (1, 0, 1)})

    def test_invalid_block_length_is_rejected(self):
        with self.assertRaises(ValueError):
            count_events_by_block("clip", [1.0], [1.0], block_seconds=0)

    def test_merge_rejects_duplicate_keys(self):
        with self.assertRaises(ValueError):
            merge_counts({("a", 0): (1, 0, 0)}, {("a", 0): (0, 1, 0)})


class MetricsTest(unittest.TestCase):
    def test_metrics_from_totals(self):
        precision, recall, f1 = metrics_from_totals(9, 7, 6)

        self.assertAlmostEqual(float(precision), 0.5625)
        self.assertAlmostEqual(float(recall), 0.6)
        self.assertAlmostEqual(float(f1), 0.5806, places=4)

    def test_zero_counts_do_not_divide_by_zero(self):
        precision, recall, f1 = metrics_from_totals(0, 0, 0)

        self.assertEqual((float(precision), float(recall), float(f1)), (0, 0, 0))


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.counts = {
            ("a", 0): (4, 1, 1),
            ("a", 1): (3, 0, 2),
            ("b", 0): (5, 2, 0),
            ("b", 1): (2, 1, 1),
        }

    def test_interval_contains_point_estimate_and_is_reproducible(self):
        first = bootstrap_metrics(self.counts, n_resamples=2000, seed=7)
        second = bootstrap_metrics(self.counts, n_resamples=2000, seed=7)

        self.assertEqual(first, second)
        f1 = first["f1"]
        self.assertAlmostEqual(f1["value"], 2 * 14 / (2 * 14 + 4 + 4))
        self.assertLessEqual(f1["ci_low"], f1["value"])
        self.assertGreaterEqual(f1["ci_high"], f1["value"])

    def test_identical_units_give_a_degenerate_interval(self):
        counts = {("a", i): (3, 1, 1) for i in range(5)}

        f1 = bootstrap_metrics(counts, n_resamples=500, seed=1)["f1"]

        self.assertAlmostEqual(f1["ci_low"], f1["value"])
        self.assertAlmostEqual(f1["ci_high"], f1["value"])

    def test_paired_difference_detects_a_consistent_improvement(self):
        baseline = {("a", i): (3, 2, 3) for i in range(12)}
        improved = {("a", i): (5, 2, 1) for i in range(12)}

        result = paired_bootstrap_difference(
            baseline, improved, n_resamples=500, seed=3
        )

        self.assertGreater(result["f1"]["difference"], 0)
        self.assertGreater(result["f1"]["ci_low"], 0)
        self.assertEqual(result["probability_b_better"], 1.0)

    def test_paired_difference_of_identical_methods_is_zero(self):
        result = paired_bootstrap_difference(
            self.counts, self.counts, n_resamples=500, seed=3
        )

        self.assertEqual(result["f1"]["difference"], 0)
        self.assertEqual(result["f1"]["ci_low"], 0)
        self.assertEqual(result["f1"]["ci_high"], 0)
        self.assertEqual(result["probability_b_better"], 0.0)

    def test_invalid_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            bootstrap_metrics(self.counts, n_resamples=0)
        with self.assertRaises(ValueError):
            bootstrap_metrics(self.counts, confidence=1.0)
        with self.assertRaises(ValueError):
            bootstrap_metrics({})


if __name__ == "__main__":
    unittest.main()
