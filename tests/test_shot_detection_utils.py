import unittest

from utils.shot_detection_utils import (
    detect_shot_frames,
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
        with self.assertRaises(ValueError):
            detect_shot_frames(ball_positions_from_y_values(range(70)), fps=0)

    def test_invalid_persistence_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            detect_shot_frames(
                ball_positions_from_y_values(range(70)),
                fps=25,
                minimum_change_frames_per_hit=0,
            )

    def test_default_threshold_matches_explicit_baseline_value(self):
        ball_positions = ball_positions_from_y_values(
            list(range(35)) + list(range(35, 0, -1))
        )

        default_result = detect_shot_frames(ball_positions, fps=25)
        explicit_result = detect_shot_frames(
            ball_positions,
            fps=25,
            minimum_change_frames_per_hit=25,
        )

        self.assertEqual(default_result, explicit_result)

    def test_selected_threshold_accepts_a_shorter_persistent_change(self):
        ball_positions = ball_positions_from_y_values(
            list(range(20)) + list(range(20, -4, -1))
        )

        baseline_result = detect_shot_frames(ball_positions, fps=25)
        selected_result = detect_shot_frames(
            ball_positions,
            fps=25,
            minimum_change_frames_per_hit=18,
        )

        self.assertEqual(baseline_result, [])
        self.assertEqual(len(selected_result), 1)


if __name__ == "__main__":
    unittest.main()
