import csv
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from benchmark.check_clip import (
    ANALYSIS_SIZE,
    check_clip,
    evaluate_requirements,
    find_cuts,
    measure_camera_drift,
    sources_row,
)

WIDTH, HEIGHT = ANALYSIS_SIZE


def textured_scene(seed):
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 255, size=(HEIGHT // 8, WIDTH // 8), dtype=np.uint8)
    return cv2.resize(base, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC).astype(
        np.float32
    )


def with_small_object(scene, index):
    frame = scene.copy()
    x = 20 + (index * 3) % (WIDTH - 40)
    cv2.circle(frame, (x, 90), 4, 255, -1)
    return frame


class FindCutsTest(unittest.TestCase):
    def test_steady_scene_has_no_cuts(self):
        scene = textured_scene(1)
        frames = [with_small_object(scene, i) for i in range(50)]

        self.assertEqual(find_cuts(frames, fps=25.0), [])

    def test_scene_change_is_reported_at_the_right_time(self):
        first, second = textured_scene(1), textured_scene(2)
        frames = [with_small_object(first, i) for i in range(30)]
        frames += [with_small_object(second, i) for i in range(30, 60)]

        cuts = find_cuts(frames, fps=25.0)

        self.assertEqual(cuts, [30 / 25.0])


class CameraDriftTest(unittest.TestCase):
    def test_static_camera_has_negligible_drift(self):
        scene = textured_scene(3)
        frames = [with_small_object(scene, i) for i in range(30)]

        self.assertLess(measure_camera_drift(frames, original_width=1280), 5.0)

    def test_large_moving_player_is_not_mistaken_for_camera_motion(self):
        scene = textured_scene(4)
        frames = []
        for index in range(30):
            frame = scene.copy()
            left = 40 + index * 4
            frame[70:150, left : left + 30] = 255 if index % 2 else 0
            frames.append(frame)

        self.assertLess(measure_camera_drift(frames, original_width=1280), 20.0)

    def test_panning_camera_is_measured_in_original_pixels(self):
        scene = textured_scene(3)
        shifted = np.roll(scene, 10, axis=1)  # 10 px at analysis size
        frames = [scene] + [shifted] * 5

        drift = measure_camera_drift(frames, original_width=1280)

        self.assertAlmostEqual(drift, 10 * (1280 / WIDTH), delta=8.0)


class EvaluateRequirementsTest(unittest.TestCase):
    metadata = {"width": 1280, "height": 720, "duration_seconds": 30.0}

    def test_all_requirements_pass_for_a_good_clip(self):
        results = evaluate_requirements(self.metadata, cuts=[], camera_drift=4.0)

        self.assertTrue(all(passed for _, passed, _ in results))

    def test_each_requirement_can_fail(self):
        failing = {
            "cuts": evaluate_requirements(self.metadata, [3.0], 4.0),
            "drift": evaluate_requirements(self.metadata, [], 500.0),
            "duration": evaluate_requirements(
                {**self.metadata, "duration_seconds": 5.0}, [], 4.0
            ),
            "resolution": evaluate_requirements(
                {**self.metadata, "width": 640, "height": 360}, [], 4.0
            ),
        }

        for name, results in failing.items():
            with self.subTest(name):
                self.assertEqual(sum(1 for _, passed, _ in results if not passed), 1)


class SourcesRowTest(unittest.TestCase):
    def test_row_has_the_same_columns_as_the_manifest(self):
        manifest = Path(__file__).resolve().parent.parent / "benchmark" / "sources.csv"
        with manifest.open(newline="", encoding="utf-8") as csv_file:
            header = next(csv.reader(csv_file))
        report = {
            "clip": "c",
            "fps": 25.0,
            "width": 1280,
            "height": 720,
            "duration_seconds": 30.04,
            "sha256": "ab",
        }

        row = next(csv.reader([sources_row(report)]))

        self.assertEqual(len(row), len(header))
        self.assertEqual(row[header.index("resolution")], "1280x720")
        self.assertEqual(row[header.index("sha256")], "ab")


class CheckClipEndToEndTest(unittest.TestCase):
    def test_synthetic_video_is_analysed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.avi"
            writer = cv2.VideoWriter(
                str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25.0, (1280, 720)
            )
            scene = cv2.resize(
                textured_scene(5).astype(np.uint8), (1280, 720)
            )
            for index in range(50):
                frame = cv2.cvtColor(scene, cv2.COLOR_GRAY2BGR)
                cv2.circle(frame, (100 + index * 10, 360), 12, (255, 255, 255), -1)
                writer.write(frame)
            writer.release()

            report = check_clip(path)

        self.assertEqual(report["frame_count"], 50)
        self.assertEqual(report["cuts_seconds"], [])
        self.assertEqual(len(report["sha256"]), 64)
        self.assertEqual((report["width"], report["height"]), (1280, 720))
        # a 2-second clip is below the minimum duration
        self.assertFalse(report["passed"])


if __name__ == "__main__":
    unittest.main()
