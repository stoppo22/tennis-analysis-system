import csv
import tempfile
import unittest
from pathlib import Path

from benchmark.run_benchmark import (
    build_report,
    count_pending_clips,
    find_predictions_path,
    load_clips,
    parse_args,
)


def write_events(path, times):
    with Path(path).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["frame", "time_seconds"])
        writer.writeheader()
        for time_seconds in times:
            writer.writerow({"frame": 0, "time_seconds": time_seconds})


def write_sources(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["clip", "split"])
        writer.writeheader()
        writer.writerows(rows)


class RunBenchmarkTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        (self.root / "annotations").mkdir()
        (self.root / "predictions").mkdir()

        write_sources(
            self.root / "sources.csv",
            [
                {"clip": "dev_x_rally_01", "split": "development"},
                {"clip": "test_y_rally_01", "split": "test"},
            ],
        )
        write_events(self.root / "annotations" / "dev_x_rally_01.csv", [1.0, 2.0, 3.0])
        write_events(self.root / "annotations" / "test_y_rally_01.csv", [1.0, 2.0])
        # Historical naming: the _rally_01 suffix is omitted for dev_x.
        write_events(self.root / "predictions" / "dev_x_base.csv", [1.0])
        write_events(self.root / "predictions" / "dev_x_new.csv", [1.0, 2.0, 3.0])
        write_events(self.root / "predictions" / "test_y_rally_01_base.csv", [1.0])
        write_events(self.root / "predictions" / "test_y_rally_01_new.csv", [1.0, 2.0])

    def args(self, *extra):
        return parse_args(
            [
                "--methods", "base", "new",
                "--sources", str(self.root / "sources.csv"),
                "--annotations", str(self.root / "annotations"),
                "--predictions", str(self.root / "predictions"),
                "--resamples", "200",
                *extra,
            ]
        )

    def test_aggregates_clips_and_compares_methods(self):
        report = build_report(self.args())

        base = report["methods"]["base"]
        new = report["methods"]["new"]
        self.assertEqual(base["events"]["ground_truth"], 5)
        self.assertEqual(base["events"]["true_positives"], 2)
        self.assertEqual(new["events"]["true_positives"], 5)
        self.assertAlmostEqual(new["overall"]["f1"]["value"], 1.0)
        self.assertGreater(report["comparison"]["f1"]["difference"], 0)

    def test_split_filter(self):
        report = build_report(self.args("--splits", "test"))

        self.assertEqual(report["clips"], ["test_y_rally_01"])
        self.assertEqual(report["methods"]["base"]["events"]["ground_truth"], 2)

    def test_unknown_split_is_an_error(self):
        with self.assertRaises(ValueError):
            load_clips(self.root / "sources.csv", splits=["nope"])

    def test_missing_predictions_are_reported(self):
        with self.assertRaises(FileNotFoundError):
            find_predictions_path(self.root / "predictions", "dev_x_rally_01", "ghost")

    def test_clips_without_annotations_are_skipped_and_counted(self):
        path = self.root / "pending_sources.csv"
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=["clip", "split", "events"])
            writer.writeheader()
            writer.writerows(
                [
                    {"clip": "dev_x_rally_01", "split": "development", "events": "3"},
                    {"clip": "new_clip", "split": "test", "events": ""},
                ]
            )

        self.assertEqual(load_clips(path), [("dev_x_rally_01", "development")])
        self.assertEqual(count_pending_clips(path), 1)
        self.assertEqual(count_pending_clips(path, splits=["development"]), 0)

    def test_zero_block_length_means_whole_clip(self):
        self.assertIsNone(self.args("--block-seconds", "0").block_seconds)


if __name__ == "__main__":
    unittest.main()
