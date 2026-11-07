import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from training import kaggle_test


def fake_report(f1):
    counts = [["game6_Clip1", 0, 28, 1, 8], ["game6_Clip1", 1, 7, 0, 0]]
    return {"metrics": {"f1": {"value": f1}}, "counts": counts}


class FindAndCheckWeightsTest(unittest.TestCase):
    def test_one_match_is_found_and_none_or_two_are_refused(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "a").mkdir()
            (Path(root) / "b").mkdir()
            (Path(root) / "a" / "m.pt").write_bytes(b"x")
            self.assertEqual(kaggle_test.find_weights(root, "m"), Path(root) / "a" / "m.pt")
            with self.assertRaises(SystemExit):
                kaggle_test.find_weights(root, "other")
            (Path(root) / "b" / "m.pt").write_bytes(b"x")
            with self.assertRaises(SystemExit):
                kaggle_test.find_weights(root, "m")

    def test_a_different_checksum_stops_the_run(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "m.pt"
            path.write_bytes(b"abc")
            with self.assertRaises(SystemExit):
                kaggle_test.check_weights(path, "0" * 64)
            kaggle_test.check_weights(path, kaggle_test.sha256(path))


class MainTest(unittest.TestCase):
    def run_main(self, work, config):
        config_path = Path(work) / "config.json"
        config_path.write_text(json.dumps(config))
        weights = Path(work) / "weights"
        weights.mkdir(exist_ok=True)
        (weights / "c.pt").write_bytes(b"control")
        (weights / "n.pt").write_bytes(b"candidate")
        reference = Path(work) / "ref.pt"
        reference.write_bytes(b"reference")
        calls = []

        def evaluate(path, *_args, **_kwargs):
            calls.append(Path(path).name)
            return fake_report(0.5)

        with mock.patch.object(kaggle_test, "prepare_dataset", return_value={"test": {"positives": 3, "negatives": 1}}), \
             mock.patch.object(kaggle_test, "evaluate", side_effect=evaluate), \
             mock.patch.object(kaggle_test, "fetch_reference", return_value=reference):
            kaggle_test.main([
                "--config", str(config_path), "--source", "src",
                "--weights-root", str(weights), "--work", str(Path(work) / "out"),
            ])
        return calls

    def config(self, stage="test"):
        return {
            "stage": stage, "imgsz": 960,
            "arms": {
                "reference": {"reference": True},
                "control": {"name": "c", "sha256": sha_of(b"control")},
                "candidate": {"name": "n", "sha256": sha_of(b"candidate")},
            },
        }

    def test_each_arm_is_scored_once_and_comparisons_are_written(self):
        with tempfile.TemporaryDirectory() as work:
            config = self.config()
            calls = self.run_main(work, config)
            self.assertEqual(sorted(calls), ["c.pt", "n.pt", "ref.pt"])
            summary = json.loads((Path(work) / "out" / "test_summary.json").read_text())
            self.assertEqual(
                sorted(summary["comparisons"]),
                ["candidate_minus_control", "candidate_minus_reference", "control_minus_reference"],
            )
            # A second run finds the reports and does not score again.
            self.assertEqual(self.run_main(work, config), [])

    def test_a_non_test_stage_is_refused(self):
        with tempfile.TemporaryDirectory() as work:
            config = self.config(stage="repeats")
            with self.assertRaises(SystemExit):
                self.run_main(work, config)


def sha_of(data):
    import hashlib

    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    unittest.main()
