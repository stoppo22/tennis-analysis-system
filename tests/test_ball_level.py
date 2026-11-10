import csv
import tempfile
import unittest
from pathlib import Path

from benchmark.ball_level import (
    best_detection,
    compare_reports,
    image_path,
    load_manifest,
    make_report,
    score_frames,
)


def row(game, clip, frame, visibility, x=100.0, y=100.0):
    return {"game": game, "clip": clip, "frame": frame, "visibility": visibility, "x": x, "y": y}


class BestDetectionTest(unittest.TestCase):
    def test_picks_the_most_confident_box_centre(self):
        boxes = [[0, 0, 10, 10], [100, 100, 120, 110]]

        self.assertEqual(best_detection(boxes, [0.2, 0.9]), (110.0, 105.0))

    def test_no_box_gives_none(self):
        self.assertIsNone(best_detection([], []))

    def test_mismatched_lengths_are_rejected(self):
        with self.assertRaises(ValueError):
            best_detection([[0, 0, 1, 1]], [])


class ManifestTest(unittest.TestCase):
    def test_load_manifest_filters_by_split_and_converts_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (Path(tmp) / "manifest.csv").open("w", newline="") as csv_file:
                writer = csv.writer(csv_file, lineterminator="\n")
                writer.writerow(["split", "game", "clip", "frame", "visibility", "x", "y"])
                writer.writerow(["validation", 3, "Clip2", 8, 1, 50.0, 60.0])
                writer.writerow(["validation", 3, "Clip2", 12, 0, "", ""])
                writer.writerow(["test", 6, "Clip1", 0, 1, 1.0, 1.0])

            rows = load_manifest(tmp, "validation")

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], row(3, "Clip2", 8, 1, 50.0, 60.0))
        self.assertIsNone(rows[1]["x"])
        self.assertEqual(
            image_path("d", "validation", rows[0]), Path("d/images/validation/game3_Clip2_0008.jpg")
        )


class ScoreFramesTest(unittest.TestCase):
    def test_scores_across_clips_and_reports_recall(self):
        rows = [
            row(3, "Clip1", 0, 1),
            row(3, "Clip1", 4, 1),
            row(8, "Clip1", 0, 1),
            row(8, "Clip1", 4, 0, None, None),
        ]
        detections = [(101.0, 100.0), None, (500.0, 500.0), (10.0, 10.0)]

        counts, summary = score_frames(rows, detections, tolerance_pixels=16)
        report = make_report(counts, summary, n_resamples=100)

        self.assertEqual(summary, {"visible": 3, "found": 1, "absent": 1, "absent_with_detection": 1})
        self.assertAlmostEqual(report["recall_visible"], 1 / 3)
        self.assertEqual(report["false_detection_rate_absent"], 1.0)
        self.assertEqual(sum(values[2] for values in report["counts"]), 1)

    def test_mismatched_lengths_are_rejected(self):
        with self.assertRaises(ValueError):
            score_frames([row(3, "Clip1", 0, 1)], [], 16)

    def test_no_absent_frames_gives_no_false_detection_rate(self):
        counts, summary = score_frames([row(3, "Clip1", 0, 1)], [(100.0, 100.0)], 16)

        self.assertIsNone(make_report(counts, summary, n_resamples=10)["false_detection_rate_absent"])


class CompareTest(unittest.TestCase):
    def test_a_better_detector_gives_a_positive_difference(self):
        rows = [row(3, "Clip1", n * 4, 1) for n in range(200)]
        weak = [(100.0, 100.0) if n % 4 == 0 else None for n in range(200)]
        strong = [(100.0, 100.0) if n % 4 != 3 else None for n in range(200)]
        reports = []
        for detections in (weak, strong):
            counts, summary = score_frames(rows, detections, 16)
            reports.append(make_report(counts, summary, n_resamples=100))

        result = compare_reports(reports[0], reports[1], n_resamples=500)

        self.assertGreater(result["f1"]["difference"], 0.3)
        self.assertGreater(result["f1"]["ci_low"], 0.0)


if __name__ == "__main__":
    unittest.main()
