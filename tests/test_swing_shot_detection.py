import math
import unittest

import numpy as np

from utils.swing_shot_detection import (
    detect_swing_shot_frames,
    zigzag_pivots,
)


def triangle_wave(turning_points, samples_between):
    """Piecewise-linear signal through the given turning values."""
    segments = []
    for start, end in zip(turning_points, turning_points[1:]):
        segments.append(np.linspace(start, end, samples_between, endpoint=False))
    segments.append([turning_points[-1]])
    return np.concatenate(segments)


def positions_from_y(y_values, half_size=3.0, x=100.0):
    return [
        {1: [x - half_size, y - half_size, x + half_size, y + half_size]}
        for y in y_values
    ]


class ZigzagPivotsTest(unittest.TestCase):
    def test_finds_alternating_extrema_at_the_turning_points(self):
        signal = triangle_wave([300, 100, 300, 100, 300, 100], 20)

        pivots = zigzag_pivots(signal, threshold=50)

        # turning points at samples 20, 40, 60, 80; the ends are excluded
        self.assertEqual(pivots, [20, 40, 60, 80])
        values = signal[pivots]
        self.assertTrue(np.all(np.diff(np.sign(np.diff(values))) != 0))

    def test_wiggles_below_the_threshold_are_ignored(self):
        signal = triangle_wave([300, 100, 300, 100], 40)
        wiggle = 8 * np.sin(np.linspace(0, 60, signal.size))

        pivots = zigzag_pivots(signal + wiggle, threshold=60)

        self.assertEqual(len(pivots), 2)

    def test_start_and_end_samples_are_never_pivots(self):
        signal = triangle_wave([100, 300], 30)

        self.assertEqual(zigzag_pivots(signal, threshold=50), [])

    def test_invalid_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            zigzag_pivots(np.array([1.0, 2.0, 1.0]), threshold=0)


class DetectSwingShotFramesTest(unittest.TestCase):
    def test_detects_each_swing_extremum_in_frames(self):
        y = triangle_wave([600, 200, 600, 200, 600, 200], 25)

        frames = detect_swing_shot_frames(positions_from_y(y), fps=25.0)

        self.assertEqual(len(frames), 4)
        for found, expected in zip(frames, [25, 50, 75, 100]):
            self.assertLessEqual(abs(found - expected), 1)

    def test_threshold_scales_with_resolution(self):
        y = triangle_wave([600, 200, 600, 200, 600, 200], 25)

        small = detect_swing_shot_frames(positions_from_y(y * 0.5), fps=25.0)
        large = detect_swing_shot_frames(positions_from_y(y * 2.0), fps=25.0)

        self.assertEqual(small, large)

    def test_event_times_are_stable_across_frame_rates(self):
        seconds_between = 1.0
        times = []
        for fps in (25.0, 30.0, 60.0):
            samples = int(seconds_between * fps)
            y = triangle_wave([600, 200, 600, 200, 600, 200], samples)
            frames = detect_swing_shot_frames(positions_from_y(y), fps=fps)
            times.append([frame / fps for frame in frames])

        for found in times:
            self.assertEqual(len(found), 4)
            for value, expected in zip(found, [1.0, 2.0, 3.0, 4.0]):
                self.assertLessEqual(abs(value - expected), 0.05)

    def test_flat_trajectory_has_no_events(self):
        self.assertEqual(
            detect_swing_shot_frames(positions_from_y([300.0] * 100), fps=25.0), []
        )

    def test_missing_ball_positions_are_rejected(self):
        positions = positions_from_y([100.0, 200.0, 100.0])
        positions[1] = {}

        with self.assertRaises(ValueError):
            detect_swing_shot_frames(positions, fps=25.0)

    def test_invalid_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            detect_swing_shot_frames(
                positions_from_y([1.0, 2.0, 1.0]), fps=25.0, min_swing_ratio=0
            )


if __name__ == "__main__":
    unittest.main()
