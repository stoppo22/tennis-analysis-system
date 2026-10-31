import csv
import tempfile
import unittest
from pathlib import Path

from benchmark.compare_annotations import (
    collect_pairs,
    compare_annotations,
    pooled_agreement,
)


def write_events(path, times):
    with Path(path).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["frame", "time_seconds"])
        writer.writeheader()
        for time_seconds in times:
            writer.writerow({"frame": 0, "time_seconds": time_seconds})


class CompareAnnotationsTest(unittest.TestCase):
    def test_identical_annotations_agree_perfectly(self):
        result = compare_annotations([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])

        self.assertEqual(result["agreement_f1"], 1.0)
        self.assertEqual(result["only_first"], 0)
        self.assertEqual(result["only_second"], 0)
        self.assertEqual(result["mean_absolute_difference_seconds"], 0)

    def test_reports_unmatched_events_and_timing(self):
        result = compare_annotations([1.0, 2.0, 5.0], [1.04, 2.1, 9.0])

        self.assertEqual(result["matched"], 2)
        self.assertEqual(result["only_first"], 1)
        self.assertEqual(result["only_second"], 1)
        self.assertEqual(result["unmatched_first_times"], [5.0])
        self.assertEqual(result["unmatched_second_times"], [9.0])
        self.assertAlmostEqual(result["mean_absolute_difference_seconds"], 0.07)
        self.assertAlmostEqual(result["mean_signed_difference_seconds"], 0.07)
        self.assertAlmostEqual(result["max_absolute_difference_seconds"], 0.1)

    def test_signed_difference_exposes_a_systematic_lag(self):
        result = compare_annotations([1.0, 2.0], [0.9, 1.9])

        self.assertAlmostEqual(result["mean_signed_difference_seconds"], -0.1)

    def test_agreement_f1_does_not_depend_on_the_order(self):
        first, second = [1.0, 2.0, 3.0, 7.0], [1.1, 2.1, 9.0]

        self.assertAlmostEqual(
            compare_annotations(first, second)["agreement_f1"],
            compare_annotations(second, first)["agreement_f1"],
        )

    def test_empty_annotations_do_not_crash(self):
        result = compare_annotations([], [])

        self.assertEqual(result["agreement_f1"], 0.0)
        self.assertIsNone(result["mean_signed_difference_seconds"])


class PooledAgreementTest(unittest.TestCase):
    def test_counts_are_pooled_before_computing_f1(self):
        per_clip = {
            "a": compare_annotations([1.0, 2.0], [1.0, 2.0]),
            "b": compare_annotations([1.0, 2.0, 3.0, 4.0], [1.0]),
        }

        pooled = pooled_agreement(per_clip)

        self.assertEqual(pooled["matched"], 3)
        self.assertEqual(pooled["only_first"], 3)
        self.assertEqual(pooled["only_second"], 0)
        self.assertAlmostEqual(pooled["agreement_f1"], 6 / 9)


class CollectPairsTest(unittest.TestCase):
    def test_directories_are_paired_by_file_name(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "one", Path(directory) / "two"
            first.mkdir()
            second.mkdir()
            write_events(first / "clip_a.csv", [1.0])
            write_events(second / "clip_a.csv", [1.0])
            write_events(first / "only_in_first.csv", [1.0])

            pairs = collect_pairs(first, second)

        self.assertEqual(list(pairs), ["clip_a"])

    def test_mixing_a_file_and_a_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "a.csv"
            write_events(file_path, [1.0])

            with self.assertRaises(ValueError):
                collect_pairs(file_path, directory)

    def test_directories_without_common_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "one", Path(directory) / "two"
            first.mkdir()
            second.mkdir()
            write_events(first / "a.csv", [1.0])
            write_events(second / "b.csv", [1.0])

            with self.assertRaises(ValueError):
                collect_pairs(first, second)


if __name__ == "__main__":
    unittest.main()
