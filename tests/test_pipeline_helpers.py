import tempfile
import unittest
from pathlib import Path

import numpy as np

from tennis_analysis.pipeline import (
    _build_detection_cache_path,
    _draw_frame_overlays,
    _filter_ball_detections,
    _require_files,
    analyze_video,
)


class RequireFilesTest(unittest.TestCase):
    def test_all_missing_files_are_listed_together(self):
        with self.assertRaises(FileNotFoundError) as context:
            _require_files({"input video": "a.mp4", "ball model": "b.pt"})

        message = str(context.exception)
        self.assertIn("input video: a.mp4", message)
        self.assertIn("ball model: b.pt", message)

    def test_existing_files_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "video.mp4"
            path.write_bytes(b"x")

            _require_files({"input video": path})


class DetectionCachePathTest(unittest.TestCase):
    def test_cache_depends_on_video_and_model_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video, model = root / "v.mp4", root / "m.pt"
            video.write_bytes(b"video-1")
            model.write_bytes(b"model-1")

            first = _build_detection_cache_path(root, "ball", video, model)
            repeat = _build_detection_cache_path(root, "ball", video, model)
            video.write_bytes(b"video-2")
            changed_video = _build_detection_cache_path(root, "ball", video, model)

        self.assertEqual(first, repeat)
        self.assertNotEqual(first, changed_video)


class DrawFrameOverlaysTest(unittest.TestCase):
    def frames(self, count=20):
        return [np.zeros((360, 640, 3), dtype=np.uint8) for _ in range(count)]

    def test_shot_badge_appears_only_near_a_shot(self):
        frames = _draw_frame_overlays(self.frames(), fps=25.0, shot_frames=[5])
        badge_region = (slice(18, 62), slice(260, 415))  # right of the time panel

        self.assertTrue(frames[5][badge_region].any())
        self.assertTrue(frames[8][badge_region].any())  # within 0.35 s
        self.assertFalse(frames[0][badge_region].any())
        self.assertFalse(frames[15][badge_region].any())

    def test_every_frame_gets_the_time_panel(self):
        frames = _draw_frame_overlays(self.frames(3), fps=25.0, shot_frames=[])

        for frame in frames:
            self.assertTrue(frame[18:62, 20:250].any())


class FilterBallDetectionsTest(unittest.TestCase):
    def static_detections(self):
        return [{1: [100.0, 100.0, 112.0, 112.0]} for _ in range(60)]

    def test_nothing_changes_when_the_filter_is_off(self):
        detections = self.static_detections()

        filtered, removed = _filter_ball_detections(detections, 25.0, 1920, False)

        self.assertIs(filtered, detections)
        self.assertEqual(removed, 0)

    def test_a_fixed_mark_is_removed_when_the_filter_is_on(self):
        filtered, removed = _filter_ball_detections(self.static_detections(), 25.0, 1920, True)

        self.assertEqual(removed, 60)
        self.assertTrue(all(entry == {} for entry in filtered))


class AnalyzeVideoValidationTest(unittest.TestCase):
    def test_missing_inputs_fail_before_any_model_is_loaded(self):
        # the heavy imports happen first, so this only runs where they are installed
        try:
            import torch  # noqa: F401
            import ultralytics  # noqa: F401
        except ImportError:
            self.skipTest("PyTorch/Ultralytics not installed")

        with self.assertRaises(FileNotFoundError):
            analyze_video("missing.mp4", "out.avi")


if __name__ == "__main__":
    unittest.main()
