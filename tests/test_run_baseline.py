import unittest

from benchmark.run_baseline import validate_cached_detections


class RunBaselineTest(unittest.TestCase):
    def test_cache_must_be_a_list(self):
        with self.assertRaises(ValueError):
            validate_cached_detections({}, expected_frame_count=1)

    def test_cache_frame_count_must_match_video(self):
        with self.assertRaises(ValueError):
            validate_cached_detections([{}, {}], expected_frame_count=3)

    def test_valid_cache_is_accepted(self):
        validate_cached_detections([{}, {}], expected_frame_count=2)

if __name__ == "__main__":
    unittest.main()
