"""Train and score ball detectors on the TrackNet dataset (Kaggle or any GPU machine).

Implements the training part of ``benchmark/EXPERIMENT_ball_detector_training.md``. It
reads a JSON run configuration (``training/kaggle_run.json``), builds the YOLO dataset
from the TrackNet frames, and for every model: trains it, scores the best checkpoint on
the **validation** games with ``benchmark.ball_level`` and saves the weights, the report
and a summary. The test games are never touched here.

    python training/kaggle_train.py --config training/kaggle_run.json \
        --source /kaggle/input/tracknet-tennis/Dataset --work /kaggle/working

A model that fails (for example out of memory) is recorded and the next one is run. A
model whose report already exists is skipped, so an interrupted run can be repeated.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from benchmark.ball_level import evaluate  # noqa: E402
from benchmark.tracknet import prepare_dataset  # noqa: E402

REFERENCE_URL = (
    "https://github.com/stoppo22/tennis-analysis-system/releases/download/v1.0/yolov11best.pt"
)
REFERENCE_SHA256 = "1f74aea3f7e84ccfbf61d0633d3f0d9713b20f2a7709771b8f9afa426a315d8c"
BOX_SIDE = 14  # pixels, fixed by looking at 50 magnified frames before any training


def sha256(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def current_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, capture_output=True, text=True
        ).stdout.strip()
    except OSError:
        return ""


def fetch_reference(destination):
    destination = Path(destination)
    if not destination.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(REFERENCE_URL, destination)
    if sha256(destination) != REFERENCE_SHA256:
        raise RuntimeError("The reference checkpoint does not match its recorded SHA-256.")
    return destination


def train_one(weights, data_yaml, config, runs_dir):
    import torch
    from ultralytics import YOLO

    device = config.get("device", 0)
    model = YOLO(weights)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    started = time.time()
    model.train(
        data=str(data_yaml),
        epochs=config["epochs"],
        imgsz=config["imgsz"],
        batch=config["batch"],
        seed=config["seed"],
        deterministic=True,
        device=device,
        project=str(runs_dir),
        name=Path(weights).stem,
        workers=config.get("workers", 4),
        fraction=config.get("fraction", 1.0),
        plots=False,
        exist_ok=True,
    )
    seconds = time.time() - started
    peak = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else None
    parameters = sum(parameter.numel() for parameter in model.model.parameters())
    return Path(model.trainer.best), {
        "train_seconds": seconds,
        "peak_gpu_gb": peak,
        "parameters_million": parameters / 1e6,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--config", required=True)
    parser.add_argument("--source", required=True, help="TrackNet ``Dataset`` directory.")
    parser.add_argument("--work", required=True, help="Output directory.")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text())
    work = Path(args.work)
    dataset = work / "tracknet_yolo"
    reports, weights_dir, runs = work / "reports", work / "weights", work / "runs"
    for directory in (reports, weights_dir, runs):
        directory.mkdir(parents=True, exist_ok=True)

    if not (dataset / "data.yaml").is_file():
        totals = prepare_dataset(args.source, dataset, BOX_SIDE)
        print("dataset:", totals, flush=True)

    summary = {"commit": current_commit(), "config": config, "models": {}}
    eval_options = {"limit": config.get("eval_limit"), "device": config.get("device", 0)}

    if config.get("reference", True):
        report_path = reports / "reference.json"
        if not report_path.is_file():
            reference = fetch_reference(work / "reference" / "yolov11best.pt")
            report = evaluate(reference, dataset, "validation", config["imgsz"], **eval_options)
            report_path.write_text(json.dumps(report, indent=2))
        summary["models"]["reference"] = {"report": str(report_path)}

    for weights in config["models"]:
        name = f"{Path(weights).stem}_seed{config['seed']}"
        report_path = reports / f"{name}.json"
        if report_path.is_file():
            print(f"{name}: report exists, skipped", flush=True)
            continue
        entry = {}
        try:
            best, info = train_one(weights, dataset / "data.yaml", config, runs)
            target = weights_dir / f"{name}.pt"
            target.write_bytes(best.read_bytes())
            report = evaluate(target, dataset, "validation", config["imgsz"], **eval_options)
            report.update(info)
            report["sha256"] = sha256(target)
            report_path.write_text(json.dumps(report, indent=2))
            entry = {"report": str(report_path), **info}
            print(f"{name}: validation F1 {report['metrics']['f1']['value']:.3f}", flush=True)
        except Exception as error:  # noqa: BLE001 - record any failure and go on
            entry = {"error": f"{type(error).__name__}: {error}"}
            print(f"{name}: FAILED {entry['error']}", flush=True)
        summary["models"][name] = entry
        (work / "summary.json").write_text(json.dumps(summary, indent=2))

    (work / "summary.json").write_text(json.dumps(summary, indent=2))
    print("done", flush=True)


if __name__ == "__main__":
    main()
