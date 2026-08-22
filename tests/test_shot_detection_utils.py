import math
import unittest

from utils.shot_detection_utils import (
    detect_shot_frames,
    duration_to_frames,
    duration_to_odd_frames,
    interpolate_ball_positions,
)


def ball_positions_from_y_values(y_values):
    return [{1: [0, y, 2, y + 2]} for y in y_values]


class ShotDetectionUtilsTest(unittest.TestCase):
    def test_interpolation_fills_missing_ball_position(self):
        positions = [
            {1: [0, 0, 2, 2]},
            {},
            {1: [2, 2, 4, 4]},
        ]

        interpolated = interpolate_ball_positions(positions)

        self.assertEqual(interpolated[1][1], [1.0, 1.0, 3.0, 3.0])

    def test_interpolation_rejects_video_without_ball_detections(self):
        with self.assertRaises(ValueError):
            interpolate_ball_positions([{}, {}])

    def test_detects_persistent_vertical_direction_change(self):
        y_values = list(range(35)) + list(range(35, 0, -1))

        shot_frames = detect_shot_frames(
            ball_positions_from_y_values(y_values),
            fps=25,
        )

        self.assertEqual(len(shot_frames), 1)

    def test_monotonic_trajectory_has_no_shot(self):
        shot_frames = detect_shot_frames(
            ball_positions_from_y_values(range(70)),
            fps=25,
        )

        self.assertEqual(shot_frames, [])

    def test_invalid_fps_is_rejected(self):
        for fps in (0, -1, math.inf, math.nan):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                detect_shot_frames(ball_positions_from_y_values(range(70)), fps=fps)

    def test_invalid_durations_are_rejected(self):
        for duration in (0, -1, math.inf, math.nan):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                detect_shot_frames(
                    ball_positions_from_y_values(range(70)),
                    fps=25,
                    persistence_seconds=duration,
                )

    def test_duration_conversion_at_common_frame_rates(self):
        self.assertEqual(duration_to_frames(0.72, 25), 18)
        self.assertEqual(duration_to_frames(0.72, 30), 22)
        self.assertEqual(duration_to_frames(0.72, 60), 43)

    def test_smoothing_conversion_uses_odd_windows(self):
        self.assertEqual(duration_to_odd_frames(0.20, 25), 5)
        self.assertEqual(duration_to_odd_frames(0.20, 30), 7)
        self.assertEqual(duration_to_odd_frames(0.20, 60), 13)

    def test_one_second_matches_historical_25_frame_baseline(self):
        ball_positions = ball_positions_from_y_values(
            list(range(35)) + list(range(35, 0, -1))
        )

        result = detect_shot_frames(
            ball_positions,
            fps=25,
            persistence_seconds=1.0,
        )

        self.assertEqual(len(result), 1)

    def test_selected_threshold_accepts_a_shorter_persistent_change(self):
        ball_positions = ball_positions_from_y_values(
            list(range(20)) + list(range(20, -4, -1))
        )

        baseline_result = detect_shot_frames(
            ball_positions,
            fps=25,
            persistence_seconds=1.0,
        )
        selected_result = detect_shot_frames(
            ball_positions,
            fps=25,
            persistence_seconds=0.72,
        )

        self.assertEqual(baseline_result, [])
        self.assertEqual(len(selected_result), 1)

    def test_equivalent_trajectories_have_consistent_event_times(self):
        event_times = []

        for fps in (25, 30, 60):
            y_values = [min(frame, 2 * fps - frame) for frame in range(4 * fps)]
            shot_frames = detect_shot_frames(
                ball_positions_from_y_values(y_values),
                fps=fps,
            )

            self.assertEqual(len(shot_frames), 1)
            event_times.append(shot_frames[0] / fps)

        self.assertLessEqual(max(event_times) - min(event_times), 1 / 25)


if __name__ == "__main__":
    unittest.main()
