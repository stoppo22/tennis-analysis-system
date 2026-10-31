"""Regression test: the shot detector must reproduce the frozen predictions.

The ball detections of both benchmark clips are stored as CSV, so the real
benchmark data can be re-run without videos or model weights.
"""

import csv
import unittest
from pathlib import Path

from benchmark.detections import load_detections_csv
from tennis_analysis.utils.shot_detection_utils import (
    detect_shot_frames,
    interpolate_ball_positions,
)
from tennis_analysis.utils.swing_shot_detection import detect_swing_shot_frames

BENCHMARK = Path(__file__).resolve().parent.parent / "benchmark"
FPS = 25.0

CLIPS = {
    "development_australian_open_2024_sinner_medvedev_rally_01": (
        "development_australian_open_2024_sinner_medvedev"
    ),
    "test_wimbledon_2025_sinner_djokovic_rally_01": (
        "test_wimbledon_2025_sinner_djokovic"
    ),
}
METHODS = {"baseline": 1.0, "persistence_18": 0.72}


def read_frames(path):
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [int(row["frame"]) for row in csv.DictReader(csv_file)]


class FrozenBenchmarkTest(unittest.TestCase):
    def test_detections_reproduce_frozen_predictions(self):
        for clip, prediction_stem in CLIPS.items():
            detections = load_detections_csv(BENCHMARK / "detections" / f"{clip}.csv")
            positions = interpolate_ball_positions(detections)

            for method, persistence_seconds in METHODS.items():
                with self.subTest(clip=clip, method=method):
                    expected = read_frames(
                        BENCHMARK / "predictions" / f"{prediction_stem}_{method}.csv"
                    )
                    predicted = detect_shot_frames(
                        positions,
                        FPS,
                        persistence_seconds=persistence_seconds,
                    )

                    self.assertEqual([int(frame) for frame in predicted], expected)

    def test_swing_detector_reproduces_frozen_predictions(self):
        for clip, prediction_stem in CLIPS.items():
            with self.subTest(clip=clip):
                positions = interpolate_ball_positions(
                    load_detections_csv(BENCHMARK / "detections" / f"{clip}.csv")
                )
                expected = read_frames(
                    BENCHMARK / "predictions" / f"{prediction_stem}_swing_v1.csv"
                )

                predicted = detect_swing_shot_frames(positions, FPS)

                self.assertEqual([int(frame) for frame in predicted], expected)


if __name__ == "__main__":
    unittest.main()
