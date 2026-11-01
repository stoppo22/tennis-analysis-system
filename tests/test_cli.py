import unittest

from tennis_analysis.cli import parse_args


class CliArgumentsTest(unittest.TestCase):
    def test_statistics_output_defaults_to_automatic_path(self):
        args = parse_args([])

        self.assertIsNone(args.statistics_output)

    def test_statistics_output_accepts_explicit_path(self):
        args = parse_args(
            [
                "--input",
                "input.mp4",
                "--output",
                "output.avi",
                "--statistics-output",
                "statistics.csv",
            ]
        )

        self.assertEqual(args.input, "input.mp4")
        self.assertEqual(args.output, "output.avi")
        self.assertEqual(args.statistics_output, "statistics.csv")

    def test_defaults_preserve_the_documented_behaviour(self):
        args = parse_args([])

        self.assertEqual(args.shot_detector, "persistence")
        self.assertEqual(args.player_model, "yolo11l.pt")
        self.assertEqual(args.ball_model, "models/yolov11best.pt")
        self.assertEqual(args.court_model, "models/keypoints_model.pth")
        self.assertEqual(args.cache_dir, "tracker_stubs")

    def test_model_paths_and_detector_can_be_overridden(self):
        args = parse_args(
            [
                "--shot-detector",
                "swing",
                "--ball-model",
                "weights/ball.pt",
                "--cache-dir",
                "/tmp/cache",
            ]
        )

        self.assertEqual(args.shot_detector, "swing")
        self.assertEqual(args.ball_model, "weights/ball.pt")
        self.assertEqual(args.cache_dir, "/tmp/cache")

    def test_static_suppression_is_off_by_default_and_can_be_enabled(self):
        self.assertFalse(parse_args([]).suppress_static)
        self.assertTrue(parse_args(["--suppress-static"]).suppress_static)

    def test_unknown_shot_detector_is_rejected(self):
        with self.assertRaises(SystemExit):
            parse_args(["--shot-detector", "magic"])


if __name__ == "__main__":
    unittest.main()
