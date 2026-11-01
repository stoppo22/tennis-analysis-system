import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from benchmark.detections import save_detections_csv
from benchmark.evaluate_events import load_event_times
from benchmark.predict_from_detections import (
    METHODS,
    clips_with_fps,
    main,
    predict_clip,
)


def zigzag_detections(turning_values, samples_between):
    values = []
    for start, end in zip(turning_values, turning_values[1:]):
        values.extend(np.linspace(start, end, samples_between, endpoint=False))
    values.append(turning_values[-1])
    return [{1: [100.0, y - 3, 106.0, y + 3]} for y in values]


class PredictFromDetectionsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.detections = self.root / "detections"
        self.output = self.root / "predictions"
        self.sources = self.root / "sources.csv"

        with self.sources.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=["clip", "split", "fps", "resolution"])
            writer.writeheader()
            writer.writerows(
                [
                    {"clip": "rally", "split": "test", "fps": "25", "resolution": "1920x1080"},
                    {"clip": "empty", "split": "test", "fps": "50", "resolution": "1920x1080"},
                    {"clip": "other", "split": "development", "fps": "25", "resolution": "1280x720"},
                    {"clip": "absent", "split": "test", "fps": "25", "resolution": "1920x1080"},
                ]
            )

        save_detections_csv(
            zigzag_detections([600, 200, 600, 200, 600, 200, 600], 30),
            self.detections / "rally.csv",
        )
        save_detections_csv([{}] * 100, self.detections / "empty.csv")

    def test_only_the_requested_splits_with_a_frame_rate_are_used(self):
        self.assertEqual(
            clips_with_fps(self.sources, {"test"}),
            {"rally": 25.0, "empty": 50.0, "absent": 25.0},
        )

    def test_clip_without_any_detection_has_no_events(self):
        for method in METHODS:
            with self.subTest(method):
                self.assertEqual(predict_clip([{}] * 50, 25.0, method), [])

    def test_writes_one_file_per_method_and_clip_with_detections(self):
        main(
            [
                "--splits", "test",
                "--detections", str(self.detections),
                "--sources", str(self.sources),
                "--output-dir", str(self.output),
            ]
        )

        written = sorted(path.name for path in self.output.glob("*.csv"))
        expected = sorted(
            f"{clip}_{method}.csv" for clip in ("rally", "empty") for method in METHODS
        )
        self.assertEqual(written, expected)
        self.assertGreaterEqual(len(load_event_times(self.output / "rally_swing_v1.csv")), 3)
        self.assertEqual(load_event_times(self.output / "empty_swing_v1.csv"), [])

    def test_suppress_static_removes_a_fixed_mark_and_renames_the_files(self):
        # a fixed mark reported in every frame, plus a real swinging ball
        ball = zigzag_detections([600, 200, 600, 200, 600, 200, 600], 30)
        for entry in ball:
            entry[1] = [900.0, 700.0, 912.0, 712.0]  # the mark overrides the ball
        save_detections_csv(ball, self.detections / "rally.csv")

        main(
            [
                "--splits", "test", "--methods", "swing_v1", "--suppress-static",
                "--detections", str(self.detections),
                "--sources", str(self.sources),
                "--output-dir", str(self.output),
            ]
        )

        self.assertEqual(load_event_times(self.output / "rally_swing_v1_nostatic.csv"), [])
        self.assertFalse((self.output / "rally_swing_v1.csv").exists())

    def test_tag_is_appended_to_the_file_names(self):
        main(
            [
                "--splits", "test", "--methods", "swing_v1", "--suppress-static",
                "--tag", "conf",
                "--detections", str(self.detections),
                "--sources", str(self.sources),
                "--output-dir", str(self.output),
            ]
        )

        self.assertTrue((self.output / "rally_swing_v1_nostatic_conf.csv").exists())

    def test_predictions_are_in_seconds_of_the_clip_frame_rate(self):
        main(
            [
                "--splits", "test", "--methods", "swing_v1",
                "--detections", str(self.detections),
                "--sources", str(self.sources),
                "--output-dir", str(self.output),
            ]
        )

        times = load_event_times(self.output / "rally_swing_v1.csv")
        for found, expected in zip(times, [1.2, 2.4, 3.6, 4.8]):
            self.assertAlmostEqual(found, expected, delta=0.12)


if __name__ == "__main__":
    unittest.main()
