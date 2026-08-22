import unittest

from benchmark.run_baseline import parse_args, validate_cached_detections


class RunBaselineTest(unittest.TestCase):
    def test_cache_must_be_a_list(self):
        with self.assertRaises(ValueError):
            validate_cached_detections({}, expected_frame_count=1)

    def test_cache_frame_count_must_match_video(self):
        with self.assertRaises(ValueError):
            validate_cached_detections([{}, {}], expected_frame_count=3)

    def test_valid_cache_is_accepted(self):
        validate_cached_detections([{}, {}], expected_frame_count=2)

    def test_cli_uses_historical_baseline_durations_by_default(self):
        args = parse_args(["--video", "clip.mp4", "--output", "events.csv"])

        self.assertEqual(args.persistence_seconds, 1.0)
        self.assertEqual(args.smoothing_seconds, 0.20)

    def test_cli_accepts_time_based_thresholds(self):
        args = parse_args(
            [
                "--video",
                "clip.mp4",
                "--output",
                "events.csv",
                "--persistence-seconds",
                "0.72",
                "--smoothing-seconds",
                "0.20",
            ]
        )

        self.assertEqual(args.persistence_seconds, 0.72)
        self.assertEqual(args.smoothing_seconds, 0.20)

if __name__ == "__main__":
    unittest.main()
