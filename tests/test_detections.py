import pickle
import tempfile
import unittest
from pathlib import Path

from benchmark.detections import (
    export_cache,
    load_detections_csv,
    save_detections_csv,
)


class DetectionsCsvTest(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.directory = Path(temporary_directory.name)

    def test_round_trip_preserves_missing_frames_and_boxes(self):
        detections = [{1: [1.0, 2.0, 3.0, 4.0]}, {}, {1: [5.5, 6.5, 7.5, 8.5]}]
        path = self.directory / "clip.csv"

        save_detections_csv(detections, path)

        self.assertEqual(load_detections_csv(path), detections)

    def test_missing_frames_are_written_as_empty_cells(self):
        path = self.directory / "clip.csv"

        save_detections_csv([{}, {1: [1, 2, 3, 4]}], path)

        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "frame,x1,y1,x2,y2")
        self.assertEqual(lines[1], "0,,,,")

    def test_rejects_non_list_and_malformed_boxes(self):
        with self.assertRaises(ValueError):
            save_detections_csv({}, self.directory / "a.csv")
        with self.assertRaises(ValueError):
            save_detections_csv([{1: [1, 2, 3]}], self.directory / "b.csv")
        with self.assertRaises(ValueError):
            save_detections_csv([{1: [1, 2, 3, float("nan")]}], self.directory / "c.csv")

    def test_rejects_non_consecutive_frames_and_partial_boxes(self):
        path = self.directory / "bad.csv"
        path.write_text("frame,x1,y1,x2,y2\n0,,,,\n2,,,,\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_detections_csv(path)

        path.write_text("frame,x1,y1,x2,y2\n0,1,2,,\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_detections_csv(path)

    def test_export_cache_converts_a_pickle(self):
        detections = [{1: [1.0, 2.0, 3.0, 4.0]}, {}]
        cache = self.directory / "cache.pkl"
        cache.write_bytes(pickle.dumps(detections))
        output = self.directory / "out" / "clip.csv"

        export_cache(cache, output)

        self.assertEqual(load_detections_csv(output), detections)


if __name__ == "__main__":
    unittest.main()
