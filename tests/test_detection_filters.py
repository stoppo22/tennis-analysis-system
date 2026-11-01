import unittest

from tennis_analysis.utils.detection_filters import suppress_static_detections


def box(x, y, half=6.0):
    return {1: [x - half, y - half, x + half, y + half]}


class SuppressStaticDetectionsTest(unittest.TestCase):
    def test_a_fixed_mark_reported_for_two_seconds_is_removed(self):
        detections = [box(800, 500) for _ in range(50)]

        filtered, removed = suppress_static_detections(detections, fps=25.0, frame_width=1920)

        self.assertEqual(removed, 50)
        self.assertTrue(all(entry == {} for entry in filtered))

    def test_a_moving_ball_is_kept(self):
        detections = [box(100 + 40 * i, 500 - 3 * i) for i in range(40)]

        filtered, removed = suppress_static_detections(detections, fps=25.0, frame_width=1920)

        self.assertEqual(removed, 0)
        self.assertEqual(filtered, detections)

    def test_a_short_pause_below_the_duration_is_kept(self):
        detections = [box(800, 500) for _ in range(20)]  # 0.8 s at 25 FPS

        _, removed = suppress_static_detections(detections, fps=25.0, frame_width=1920)

        self.assertEqual(removed, 0)

    def test_only_the_static_detections_are_removed_and_numbering_is_preserved(self):
        detections = []
        for i in range(60):
            detections.append(box(900, 700))  # static mark in every frame
            detections[-1] = detections[-1] if i % 2 == 0 else box(100 + 20 * i, 300)

        filtered, removed = suppress_static_detections(detections, fps=25.0, frame_width=1920)

        self.assertEqual(len(filtered), len(detections))
        self.assertEqual(removed, 30)
        for i, entry in enumerate(filtered):
            self.assertEqual(entry, {} if i % 2 == 0 else detections[i])

    def test_missing_frames_are_left_empty(self):
        detections = [{}, box(800, 500), {}] + [box(800, 500) for _ in range(40)]

        filtered, _ = suppress_static_detections(detections, fps=25.0, frame_width=1920)

        self.assertEqual(filtered[0], {})
        self.assertEqual(len(filtered), len(detections))

    def test_the_radius_scales_with_the_frame_width(self):
        jitter = [box(800 + (i % 3) * 8, 500) for i in range(50)]  # 8 px steps

        _, removed_wide = suppress_static_detections(jitter, fps=25.0, frame_width=1920)
        _, removed_narrow = suppress_static_detections(jitter, fps=25.0, frame_width=320)

        self.assertEqual(removed_wide, 50)
        self.assertEqual(removed_narrow, 0)

    def test_the_input_is_not_modified(self):
        detections = [box(800, 500) for _ in range(50)]
        snapshot = [dict(entry) for entry in detections]

        suppress_static_detections(detections, fps=25.0, frame_width=1920)

        self.assertEqual(detections, snapshot)

    def test_invalid_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            suppress_static_detections([], fps=0, frame_width=1920)
        with self.assertRaises(ValueError):
            suppress_static_detections([], fps=25.0, frame_width=0)
        with self.assertRaises(ValueError):
            suppress_static_detections([], fps=25.0, frame_width=1920, min_seconds=0)

    def test_empty_input(self):
        self.assertEqual(suppress_static_detections([], 25.0, 1920), ([], 0))


if __name__ == "__main__":
    unittest.main()
