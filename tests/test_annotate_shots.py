import csv
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from benchmark.annotate_shots import (
    close_windows,
    add_shot_frame,
    frame_to_seconds,
    save_annotations,
)


class AnnotateShotsTest(unittest.TestCase):
    def test_frame_to_seconds_uses_source_fps(self):
        self.assertEqual(frame_to_seconds(50, 25), 2)
        self.assertAlmostEqual(frame_to_seconds(60, 59.94), 1.001001)

    def test_shot_frames_are_unique_and_keep_insertion_order(self):
        shot_frames = [20]

        self.assertTrue(add_shot_frame(shot_frames, 10))
        self.assertFalse(add_shot_frame(shot_frames, 20))
        self.assertEqual(shot_frames, [20, 10])

    def test_annotations_are_saved_as_frame_and_time(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "annotations.csv"
            save_annotations(output_path, [50, 25], fps=25)

            with output_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(
            rows,
            [
                {"frame": "25", "time_seconds": "1.000000"},
                {"frame": "50", "time_seconds": "2.000000"},
            ],
        )


class CloseWindowsTest(unittest.TestCase):
    def test_windows_are_destroyed_and_events_are_processed_afterwards(self):
        calls = []
        with mock.patch("benchmark.annotate_shots.cv2") as fake_cv2:
            fake_cv2.destroyAllWindows.side_effect = lambda: calls.append("destroy")
            fake_cv2.waitKey.side_effect = lambda _delay: calls.append("pump")

            close_windows(event_pumps=3)

        self.assertEqual(calls, ["destroy", "pump", "pump", "pump"])


if __name__ == "__main__":
    unittest.main()
