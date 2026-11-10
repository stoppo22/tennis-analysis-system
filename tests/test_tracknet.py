import csv
import tempfile
import unittest
from pathlib import Path

from benchmark.bootstrap import bootstrap_metrics
from benchmark.tracknet import (
    BLOCK_FRAMES,
    SPLITS,
    ball_frame_counts,
    list_clips,
    merge_summaries,
    prepare_dataset,
    read_labels,
    select_rows,
    split_of_game,
    yolo_label_line,
)


def write_clip(root, game, clip, rows):
    directory = Path(root) / f"game{game}" / f"Clip{clip}"
    directory.mkdir(parents=True)
    with (directory / "Label.csv").open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(["file name", "visibility", "x-coordinate", "y-coordinate", "status"])
        for number, visibility, x, y in rows:
            writer.writerow([f"{number:04d}.jpg", visibility, x, y, 0])
            (directory / f"{number:04d}.jpg").write_bytes(b"jpeg")
    return directory


class SplitTest(unittest.TestCase):
    def test_every_game_is_in_exactly_one_split(self):
        games = [g for games in SPLITS.values() for g in games]
        self.assertEqual(sorted(games), list(range(1, 11)))

    def test_each_split_has_a_clay_video(self):
        clay = {4, 6, 8}
        for split, games in SPLITS.items():
            self.assertTrue(clay & set(games), split)

    def test_split_lookup(self):
        self.assertEqual(split_of_game(6), "test")
        self.assertEqual(split_of_game(3), "validation")
        with self.assertRaises(ValueError):
            split_of_game(11)


class LabelTest(unittest.TestCase):
    def test_read_labels_and_blank_coordinates(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = write_clip(tmp, 1, 1, [(0, 1, 599, 423), (1, 0, "", "")])
            rows = read_labels(directory / "Label.csv")

        self.assertEqual(rows[0]["number"], 0)
        self.assertEqual((rows[0]["x"], rows[0]["y"]), (599.0, 423.0))
        self.assertIsNone(rows[1]["x"])

    def test_select_rows_strides_and_keeps_classes_zero_and_one_only(self):
        rows = [
            {"frame": f"{i:04d}.jpg", "number": i, "visibility": v, "x": 1.0, "y": 1.0}
            for i, v in enumerate([1, 1, 1, 1, 2, 0, 3, 1, 1, 0, 1, 1])
        ]

        kept = select_rows(rows, stride=4)

        self.assertEqual([r["number"] for r in kept], [0, 8])  # frame 4 is class 2

    def test_a_visible_row_without_coordinates_is_dropped(self):
        rows = [{"frame": "0000.jpg", "number": 0, "visibility": 1, "x": None, "y": None}]

        self.assertEqual(select_rows(rows, 1), [])


class YoloLabelTest(unittest.TestCase):
    def test_box_is_centred_and_normalised(self):
        line = yolo_label_line(640, 360, 16)

        self.assertEqual(line, "0 0.500000 0.500000 0.012500 0.022222")

    def test_box_is_clipped_at_the_border(self):
        parts = yolo_label_line(2, 360, 16).split()

        self.assertAlmostEqual(float(parts[3]), 10 / 1280, places=5)
        self.assertAlmostEqual(float(parts[1]), 5 / 1280, places=5)

    def test_point_outside_the_image_is_rejected(self):
        with self.assertRaises(ValueError):
            yolo_label_line(2000, 360, 16)


class PrepareDatasetTest(unittest.TestCase):
    def test_writes_split_folders_labels_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "src", Path(tmp) / "out"
            write_clip(source, 1, 1, [(0, 1, 100, 100), (1, 1, 110, 100), (2, 0, "", "")])
            write_clip(source, 3, 2, [(0, 0, "", ""), (1, 1, 50, 50)])
            write_clip(source, 6, 1, [(0, 1, 300, 300)])

            totals = prepare_dataset(source, output, box_side=14, stride=1)

            self.assertEqual(totals["train"], {"positives": 2, "negatives": 1})
            self.assertEqual(totals["validation"], {"positives": 1, "negatives": 1})
            self.assertEqual(totals["test"], {"positives": 1, "negatives": 0})
            self.assertTrue((output / "images" / "train" / "game1_Clip1_0000.jpg").is_file())
            label = (output / "labels" / "train" / "game1_Clip1_0000.txt").read_text()
            self.assertTrue(label.startswith("0 "))
            negative = (output / "labels" / "train" / "game1_Clip1_0002.txt").read_text()
            self.assertEqual(negative, "")
            self.assertIn("val: images/validation", (output / "data.yaml").read_text())
            with (output / "manifest.csv").open(encoding="utf-8") as csv_file:
                self.assertEqual(len(list(csv.DictReader(csv_file))), 6)

    def test_clips_are_listed_in_numeric_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            for clip in (10, 2, 1):
                write_clip(tmp, 1, clip, [(0, 1, 1, 1)])

            names = [name for _, name, _ in list_clips(tmp)]

        self.assertEqual(names, ["Clip1", "Clip2", "Clip10"])


class BallLevelScoringTest(unittest.TestCase):
    def test_found_wrong_missed_and_false_detections(self):
        frames = [
            (0, 1, (100, 100), (105, 100)),   # found
            (1, 1, (100, 100), (400, 400)),   # wrong place: miss and false positive
            (2, 1, (100, 100), None),         # missed
            (3, 0, None, (50, 50)),           # detection with no ball in the image
            (4, 0, None, None),               # correctly empty
        ]

        counts, summary = ball_frame_counts("clip", frames, tolerance_pixels=16)

        self.assertEqual(counts[("clip", 0)], (1, 2, 2))
        self.assertEqual(
            summary, {"visible": 3, "found": 1, "absent": 2, "absent_with_detection": 1}
        )

    def test_blocks_follow_the_frame_number(self):
        frames = [
            (0, 1, (1, 1), (1, 1)),
            (BLOCK_FRAMES, 1, (1, 1), (1, 1)),
        ]

        counts, _ = ball_frame_counts("c", frames, 16)

        self.assertEqual(sorted(counts), [("c", 0), ("c", 1)])

    def test_counts_feed_the_existing_bootstrap(self):
        frames = [(i, 1, (1, 1), (1, 1) if i % 2 == 0 else None) for i in range(400)]
        counts, summary = ball_frame_counts("c", frames, 16)

        result = bootstrap_metrics(counts, n_resamples=200, seed=0)

        self.assertAlmostEqual(result["recall"]["value"], 0.5)
        self.assertAlmostEqual(result["precision"]["value"], 1.0)
        self.assertEqual(merge_summaries([summary, summary])["visible"], 800)


if __name__ == "__main__":
    unittest.main()
