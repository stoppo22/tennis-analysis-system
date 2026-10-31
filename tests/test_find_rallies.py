import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from benchmark.find_rallies import (
    format_timestamp,
    scan_cuts,
    segments_from_cuts,
)


class SegmentsFromCutsTest(unittest.TestCase):
    def test_short_segments_are_dropped_and_margins_trimmed(self):
        segments = segments_from_cuts(
            cut_times=[5.0, 25.0, 28.0],
            duration_seconds=60.0,
            min_seconds=8.0,
            margin_seconds=0.5,
        )

        self.assertEqual(
            segments,
            [
                {"start": 5.5, "end": 24.5, "duration": 19.0},
                {"start": 28.5, "end": 60.0, "duration": 31.5},
            ],
        )

    def test_first_segment_is_not_trimmed_at_the_start(self):
        segments = segments_from_cuts([10.0], 30.0, min_seconds=5.0, margin_seconds=1.0)

        self.assertEqual(segments[0]["start"], 0.0)
        self.assertEqual(segments[0]["end"], 9.0)

    def test_long_segments_are_capped(self):
        segments = segments_from_cuts([], 300.0, max_seconds=60.0)

        self.assertEqual(segments, [{"start": 0.0, "end": 60.0, "duration": 60.0}])

    def test_no_segments_when_everything_is_short(self):
        self.assertEqual(segments_from_cuts([2.0, 4.0, 6.0], 8.0), [])


class FormatTimestampTest(unittest.TestCase):
    def test_hours_minutes_seconds(self):
        self.assertEqual(format_timestamp(3725.9), "01:02:05")


class ScanCutsTest(unittest.TestCase):
    def test_finds_cuts_in_a_synthetic_video(self):
        rng = np.random.default_rng(0)
        scenes = [
            cv2.resize(
                rng.integers(0, 255, size=(8, 16), dtype=np.uint8),
                (640, 360),
                interpolation=cv2.INTER_CUBIC,
            )
            for _ in range(3)
        ]
        fps = 25.0
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.avi"
            writer = cv2.VideoWriter(
                str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (640, 360)
            )
            for scene in scenes:  # 2 s per scene -> cuts at 2 s and 4 s
                for index in range(50):
                    frame = cv2.cvtColor(scene, cv2.COLOR_GRAY2BGR)
                    cv2.circle(frame, (50 + index * 5, 180), 8, (255, 255, 255), -1)
                    writer.write(frame)
            writer.release()

            cuts, duration, found_fps = scan_cuts(path, stride=1)

        self.assertAlmostEqual(duration, 6.0, places=1)
        self.assertEqual(found_fps, fps)
        self.assertEqual(len(cuts), 2)
        self.assertAlmostEqual(cuts[0], 2.0, delta=0.1)
        self.assertAlmostEqual(cuts[1], 4.0, delta=0.1)


if __name__ == "__main__":
    unittest.main()
