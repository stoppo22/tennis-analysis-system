import csv
import tempfile
import unittest
from pathlib import Path

from benchmark.evaluate_events import (
    evaluate_events,
    load_event_times,
    match_events,
)


class EvaluateEventsTest(unittest.TestCase):
    def test_reports_required_metrics(self):
        metrics = evaluate_events(
            ground_truth_times=[1.0, 2.0],
            predicted_times=[0.9, 1.2, 2.1],
        )

        self.assertEqual(metrics["true_positives"], 2)
        self.assertEqual(metrics["false_positives"], 1)
        self.assertEqual(metrics["false_negatives"], 0)
        self.assertAlmostEqual(metrics["precision"], 2 / 3)
        self.assertEqual(metrics["recall"], 1)
        self.assertAlmostEqual(metrics["f1"], 0.8)
        self.assertAlmostEqual(metrics["mean_absolute_timing_error"], 0.1)

    def test_matching_maximizes_matches_before_minimizing_error(self):
        matches = match_events(
            ground_truth_times=[0.0, 0.3],
            predicted_times=[0.2, 0.5],
            tolerance_seconds=0.25,
        )

        self.assertEqual(len(matches), 2)
        self.assertAlmostEqual(matches[0]["absolute_error"], 0.2)
        self.assertAlmostEqual(matches[1]["absolute_error"], 0.2)

    def test_matching_is_one_to_one_with_duplicate_predictions(self):
        metrics = evaluate_events(
            ground_truth_times=[1.0],
            predicted_times=[0.9, 1.1],
        )

        self.assertEqual(metrics["true_positives"], 1)
        self.assertEqual(metrics["false_positives"], 1)
        self.assertEqual(metrics["false_negatives"], 0)

    def test_tolerance_boundary_is_inclusive(self):
        metrics = evaluate_events(
            ground_truth_times=[1.0],
            predicted_times=[1.25],
            tolerance_seconds=0.25,
        )

        self.assertEqual(metrics["true_positives"], 1)

    def test_invalid_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_events([1.0], [1.0], tolerance_seconds=float("nan"))

        with self.assertRaises(ValueError):
            evaluate_events([1.0], [1.0], tolerance_seconds=-0.1)

    def test_empty_events_are_handled_explicitly(self):
        both_empty = evaluate_events([], [])
        missed_event = evaluate_events([1.0], [])
        false_event = evaluate_events([], [1.0])

        self.assertEqual(both_empty["precision"], 0)
        self.assertEqual(both_empty["recall"], 0)
        self.assertEqual(both_empty["f1"], 0)
        self.assertIsNone(both_empty["mean_absolute_timing_error"])
        self.assertEqual(missed_event["false_negatives"], 1)
        self.assertEqual(false_event["false_positives"], 1)

    def test_times_from_different_fps_match_in_seconds(self):
        ground_truth_time = 25 / 25
        prediction_time = 60 / 60

        metrics = evaluate_events([ground_truth_time], [prediction_time])

        self.assertEqual(metrics["true_positives"], 1)
        self.assertEqual(metrics["mean_absolute_timing_error"], 0)

    def test_load_event_times_reads_and_sorts_csv(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "events.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=["time_seconds"])
                writer.writeheader()
                writer.writerow({"time_seconds": "2.0"})
                writer.writerow({"time_seconds": "1.0"})

            event_times = load_event_times(csv_path)

        self.assertEqual(event_times, [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
