import csv
import tempfile
import unittest
from pathlib import Path

from benchmark.annotate_pending import (
    read_manifest,
    select_clips,
    update_manifest,
)

FIELDS = ["clip", "split", "events", "notes"]


def write_manifest(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_events(path, times):
    with Path(path).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["frame", "time_seconds"])
        writer.writeheader()
        for time_seconds in times:
            writer.writerow({"frame": 0, "time_seconds": time_seconds})


class PendingAnnotationTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.annotations = self.root / "annotations"
        self.second = self.root / "second"
        self.annotations.mkdir()
        self.second.mkdir()
        self.sources = self.root / "sources.csv"
        write_manifest(
            self.sources,
            [
                {"clip": "done", "split": "test", "events": "5", "notes": ""},
                {"clip": "new_a", "split": "test", "events": "", "notes": "pending annotation"},
                {"clip": "new_b", "split": "test", "events": "", "notes": "pending annotation"},
                {"clip": "dev_new", "split": "development", "events": "", "notes": "pending annotation"},
            ],
        )

    def rows(self):
        return read_manifest(self.sources)[0]

    def test_first_pass_offers_unannotated_clips_of_the_split(self):
        clips = select_clips(self.rows(), "test", self.annotations, self.second)

        self.assertEqual(clips, ["new_a", "new_b"])

    def test_first_pass_skips_clips_that_already_have_a_file(self):
        write_events(self.annotations / "new_a.csv", [1.0])

        clips = select_clips(self.rows(), "test", self.annotations, self.second)

        self.assertEqual(clips, ["new_b"])

    def test_second_pass_needs_a_first_annotation_and_is_a_fixed_shuffle(self):
        for name in ("done", "new_a", "new_b"):
            write_events(self.annotations / f"{name}.csv", [1.0])

        first = select_clips(self.rows(), "test", self.annotations, self.second, True)
        again = select_clips(self.rows(), "test", self.annotations, self.second, True)

        self.assertEqual(sorted(first), ["done", "new_a", "new_b"])
        self.assertEqual(first, again)

    def test_second_pass_skips_clips_already_done_twice(self):
        write_events(self.annotations / "done.csv", [1.0])
        write_events(self.second / "done.csv", [1.0])

        self.assertEqual(
            select_clips(self.rows(), "test", self.annotations, self.second, True), []
        )

    def test_update_manifest_fills_counts_and_clears_the_pending_note(self):
        write_events(self.annotations / "new_a.csv", [1.0, 2.0, 3.0])

        updated, rejected = update_manifest(self.sources, self.annotations)

        row = {r["clip"]: r for r in self.rows()}["new_a"]
        self.assertEqual((updated, rejected), (["new_a"], []))
        self.assertEqual(row["events"], "3")
        self.assertEqual(row["notes"], "")
        self.assertEqual({r["clip"]: r for r in self.rows()}["new_b"]["events"], "")

    def test_clip_without_shots_is_rejected(self):
        write_events(self.annotations / "new_b.csv", [])

        updated, rejected = update_manifest(self.sources, self.annotations)

        row = {r["clip"]: r for r in self.rows()}["new_b"]
        self.assertEqual(rejected, ["new_b"])
        self.assertEqual(row["split"], "rejected")
        self.assertEqual(row["events"], "0")
        self.assertIn("not a rally", row["notes"])

    def test_clip_with_fewer_than_three_contacts_is_rejected(self):
        write_events(self.annotations / "new_a.csv", [1.0, 2.0])
        write_events(self.annotations / "new_b.csv", [1.0, 2.0, 3.0])

        updated, rejected = update_manifest(self.sources, self.annotations)

        self.assertEqual(rejected, ["new_a"])
        self.assertEqual(updated, ["new_b"])
        self.assertEqual({r["clip"]: r for r in self.rows()}["new_a"]["split"], "rejected")

    def test_update_manifest_preserves_other_rows_and_columns(self):
        before = {r["clip"]: dict(r) for r in self.rows()}

        update_manifest(self.sources, self.annotations)

        self.assertEqual({r["clip"]: dict(r) for r in self.rows()}, before)
        self.assertEqual(read_manifest(self.sources)[1], FIELDS)


if __name__ == "__main__":
    unittest.main()
