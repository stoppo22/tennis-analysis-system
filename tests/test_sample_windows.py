import unittest

from benchmark.sample_windows import (
    sample_extra_windows,
    download_command,
    format_timestamp,
    sample_windows,
    seed_from_match_id,
)

SIX_HOURS = 6 * 3600


class SampleWindowsTest(unittest.TestCase):
    def test_same_match_gives_the_same_windows(self):
        first = sample_windows("match_a", SIX_HOURS)
        second = sample_windows("match_a", SIX_HOURS)

        self.assertEqual(first, second)

    def test_different_matches_give_different_windows(self):
        self.assertNotEqual(
            sample_windows("match_a", SIX_HOURS), sample_windows("match_b", SIX_HOURS)
        )

    def test_windows_are_sorted_in_bounds_and_do_not_overlap(self):
        windows = sample_windows("match_a", 3 * 3600, windows=4, length_seconds=120)

        self.assertEqual(len(windows), 4)
        self.assertEqual(windows, sorted(windows))
        for (start, end), (next_start, _) in zip(windows, windows[1:]):
            self.assertEqual(end - start, 120)
            self.assertLessEqual(end, next_start)
        self.assertGreaterEqual(windows[0][0], 0.10 * 3 * 3600)
        self.assertLessEqual(windows[-1][1], 0.95 * 3 * 3600)

    def test_extra_windows_keep_the_originals_and_do_not_overlap_them(self):
        original = sample_windows("match_a", SIX_HOURS, windows=3, length_seconds=150)
        extra = sample_extra_windows(
            "match_a", SIX_HOURS, already=3, extra=3, length_seconds=150
        )

        self.assertEqual(original, sample_windows("match_a", SIX_HOURS))
        self.assertEqual(len(extra), 3)
        self.assertEqual(extra, sorted(extra))
        for start, _ in extra:
            for other, _ in original:
                self.assertGreaterEqual(abs(start - other), 149)

    def test_too_short_video_is_rejected(self):
        with self.assertRaises(ValueError):
            sample_windows("match_a", 300, windows=3, length_seconds=150)

    def test_invalid_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            sample_windows("match_a", SIX_HOURS, windows=0)

    def test_seed_is_stable_across_runs(self):
        self.assertEqual(seed_from_match_id("match_a"), seed_from_match_id("match_a"))

    def test_command_and_timestamp_format(self):
        self.assertEqual(format_timestamp(3725), "01:02:05")
        command = download_command("m", "https://example.com/v", 2, 3725, 3875)

        self.assertIn('--download-sections "*01:02:05-01:04:35"', command)
        self.assertIn("m_w2.%(ext)s", command)


if __name__ == "__main__":
    unittest.main()
