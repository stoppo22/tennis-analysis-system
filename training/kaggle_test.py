"""Score the chosen model, the control and the reference once on the TrackNet test games.

Implements rule 2 of ``benchmark/EXPERIMENT_ball_detector_training.md``. It reads the JSON
run configuration (``training/kaggle_run.json``, stage ``test``), builds the dataset from the
**test** games only, checks the SHA-256 of every weight file against the one recorded in the
configuration (the weights scored on the validation games), and writes one report per arm
plus the paired comparisons. No model is trained here.

    python training/kaggle_test.py --config training/kaggle_run.json \
        --source /kaggle/input/tracknet-tennis/Dataset --weights-root /kaggle/input \
        --work /kaggle/working

The test is used once: an arm whose report already exists is not scored again, and a weight
file that does not match its recorded SHA-256 stops the run before anything is scored.
"""

import argparse
import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from benchmark.ball_level import compare_reports, evaluate  # noqa: E402
from benchmark.tracknet import prepare_dataset  # noqa: E402
from training.kaggle_train import BOX_SIDE, current_commit, fetch_reference, sha256  # noqa: E402

COMPARISONS = (("reference", "candidate"), ("reference", "control"), ("control", "candidate"))


def find_weights(root, name):
    """The single ``<name>.pt`` file under ``root``."""
    matches = sorted(Path(root).glob(f"**/{name}.pt"))
    if len(matches) != 1:
        raise SystemExit(f"Expected one {name}.pt under {root}, found {len(matches)}.")
    return matches[0]


def check_weights(path, expected):
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(f"{path}: SHA-256 {actual} differs from the recorded {expected}.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--config", required=True)
    parser.add_argument("--source", required=True, help="TrackNet ``Dataset`` directory.")
    parser.add_argument("--weights-root", required=True, help="Directory that holds the weights.")
    parser.add_argument("--work", required=True, help="Output directory.")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text())
    if config.get("stage") != "test":
        raise SystemExit("The configuration is not a test stage.")
    work = Path(args.work)
    dataset, reports = work / "tracknet_yolo_test", work / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    # Resolve and verify every weight file before scoring anything.
    arms = {}
    for arm, entry in config["arms"].items():
        if entry.get("reference"):
            arms[arm] = fetch_reference(work / "reference" / "yolov11best.pt")
        else:
            arms[arm] = find_weights(args.weights_root, entry["name"])
            check_weights(arms[arm], entry["sha256"])

    totals = prepare_dataset(args.source, dataset, BOX_SIDE, splits=["test"])
    print("dataset:", totals, flush=True)
    if not totals["test"]["positives"]:
        raise SystemExit(f"No TrackNet test frames found under {args.source}.")

    options = {"limit": config.get("eval_limit"), "device": config.get("device", 0)}
    results = {}
    for arm, weights in arms.items():
        path = reports / f"test_{arm}.json"
        if path.is_file():
            print(f"{arm}: report exists, not scored again", flush=True)
        else:
            report = evaluate(weights, dataset, "test", config["imgsz"], **options)
            report["arm"], report["sha256"] = arm, sha256(weights)
            path.write_text(json.dumps(report, indent=2))
        results[arm] = json.loads(path.read_text())
        print(f"{arm}: test F1 {results[arm]['metrics']['f1']['value']:.3f}", flush=True)

    comparisons = {}
    for first, second in COMPARISONS:
        comparisons[f"{second}_minus_{first}"] = compare_reports(results[first], results[second])
    summary = {"commit": current_commit(), "config": config, "comparisons": comparisons}
    (work / "test_summary.json").write_text(json.dumps(summary, indent=2))
    for name, result in comparisons.items():
        item = result["f1"]
        print(f"{name}: F1 {item['difference']:+.4f} [{item['ci_low']:+.4f}, {item['ci_high']:+.4f}]")
    print("done", flush=True)


if __name__ == "__main__":
    main()
