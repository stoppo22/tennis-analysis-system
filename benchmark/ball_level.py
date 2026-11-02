"""Ball-level evaluation of a detector on the TrackNet dataset prepared for YOLO.

See ``EXPERIMENT_ball_detector_training.md``. The dataset directory is the output of
``python -m benchmark.tracknet prepare``. For every selected frame the most confident
box at the chosen confidence is kept; a visible frame is found if that box is within
1.25% of the frame width of the label.

    python -m benchmark.ball_level evaluate --weights models/yolov11best.pt \
        --dataset <dir> --split validation --imgsz 960 --output report.json
    python -m benchmark.ball_level compare --a report_a.json --b report_b.json
"""

import argparse
import csv
import json
import time
from pathlib import Path

from benchmark.bootstrap import (
    bootstrap_metrics,
    merge_counts,
    paired_bootstrap_difference,
)
from benchmark.tracknet import (
    IMAGE_SIZE,
    TOLERANCE_FRACTION,
    ball_frame_counts,
    merge_summaries,
)

DEFAULT_CONFIDENCE = 0.15


def load_manifest(dataset_dir, split):
    """Rows of ``manifest.csv`` for one split, with numeric fields converted."""
    rows = []
    with (Path(dataset_dir) / "manifest.csv").open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            if row["split"] != split:
                continue
            rows.append(
                {
                    "game": int(row["game"]),
                    "clip": row["clip"],
                    "frame": int(row["frame"]),
                    "visibility": int(row["visibility"]),
                    "x": float(row["x"]) if row["x"] else None,
                    "y": float(row["y"]) if row["y"] else None,
                }
            )
    return rows


def image_path(dataset_dir, split, row):
    name = f"game{row['game']}_{row['clip']}_{row['frame']:04d}.jpg"
    return Path(dataset_dir) / "images" / split / name


def best_detection(boxes, confidences):
    """Centre of the most confident box, or ``None`` if there is no box."""
    if len(boxes) != len(confidences):
        raise ValueError("Boxes and confidences must have the same length.")
    if not boxes:
        return None
    best = max(range(len(boxes)), key=lambda index: confidences[index])
    x1, y1, x2, y2 = boxes[best]
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def score_frames(rows, detections, tolerance_pixels):
    """Counts per block and a summary from manifest rows and their detections.

    ``detections`` is a list aligned with ``rows``: a centre ``(x, y)`` or ``None``.
    """
    if len(rows) != len(detections):
        raise ValueError("Rows and detections must have the same length.")
    by_clip = {}
    for row, detection in zip(rows, detections):
        label = (row["x"], row["y"]) if row["visibility"] == 1 else None
        by_clip.setdefault(f"game{row['game']}_{row['clip']}", []).append(
            (row["frame"], row["visibility"], label, detection)
        )
    counts, summaries = [], []
    for clip, frames in sorted(by_clip.items()):
        clip_counts, summary = ball_frame_counts(clip, frames, tolerance_pixels)
        counts.append(clip_counts)
        summaries.append(summary)
    return merge_counts(*counts), merge_summaries(summaries)


def make_report(counts, summary, extra=None, n_resamples=10000, seed=0):
    metrics = bootstrap_metrics(counts, n_resamples=n_resamples, seed=seed)
    visible, absent = summary["visible"], summary["absent"]
    report = {
        "summary": summary,
        "recall_visible": summary["found"] / visible if visible else 0.0,
        "false_detection_rate_absent": (
            summary["absent_with_detection"] / absent if absent else None
        ),
        "metrics": metrics,
        "counts": [[clip, block, *values] for (clip, block), values in sorted(counts.items())],
    }
    report.update(extra or {})
    return report


def evaluate(weights, dataset_dir, split, imgsz, confidence=DEFAULT_CONFIDENCE, limit=None,
             device=None):
    from ultralytics import YOLO  # imported here: heavy and optional

    rows = load_manifest(dataset_dir, split)
    if limit:
        rows = rows[:: max(1, len(rows) // limit)][:limit]
    model = YOLO(str(weights))
    paths = [str(image_path(dataset_dir, split, row)) for row in rows]

    detections = []
    started = time.time()
    options = {"conf": confidence, "imgsz": imgsz, "verbose": False, "stream": True}
    if device is not None:
        options["device"] = device
    for result in model.predict(paths, **options):
        boxes = result.boxes.xyxy.tolist()
        scores = result.boxes.conf.tolist()
        detections.append(best_detection(boxes, scores))
    seconds = time.time() - started

    tolerance = TOLERANCE_FRACTION * IMAGE_SIZE[0]
    counts, summary = score_frames(rows, detections, tolerance)
    return make_report(
        counts,
        summary,
        {
            "weights": str(weights),
            "split": split,
            "imgsz": imgsz,
            "confidence": confidence,
            "images": len(rows),
            "seconds_per_image": seconds / max(1, len(rows)),
        },
    )


def compare_reports(report_a, report_b, n_resamples=10000, seed=0):
    """Paired bootstrap of ``B - A`` from two reports on the same frames."""
    def counts(report):
        return {(clip, block): tuple(values) for clip, block, *values in report["counts"]}

    return paired_bootstrap_difference(
        counts(report_a), counts(report_b), n_resamples=n_resamples, seed=seed
    )


def _print_report(report):
    metrics = report["metrics"]
    summary = report["summary"]
    print(
        f"{report.get('weights', '')} {report.get('split', '')} imgsz {report.get('imgsz', '')}: "
        f"{report.get('images', summary['visible'] + summary['absent'])} frames"
    )
    print(
        f"  recall on visible frames: {report['recall_visible']:.3f} "
        f"({summary['found']} of {summary['visible']})"
    )
    absent = report["false_detection_rate_absent"]
    if absent is not None:
        print(
            f"  detections on frames without a ball: {absent:.3f} "
            f"({summary['absent_with_detection']} of {summary['absent']})"
        )
    for name in ("precision", "recall", "f1"):
        item = metrics[name]
        print(f"  {name}: {item['value']:.3f} [{item['ci_low']:.3f}, {item['ci_high']:.3f}]")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("evaluate")
    run.add_argument("--weights", required=True)
    run.add_argument("--dataset", required=True)
    run.add_argument("--split", choices=["validation", "test"], required=True)
    run.add_argument("--imgsz", type=int, default=960)
    run.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    run.add_argument("--limit", type=int, help="Evaluate only this many frames (smoke tests).")
    run.add_argument("--device")
    run.add_argument("--output")
    compare = sub.add_parser("compare")
    compare.add_argument("--a", required=True, help="Report of the reference.")
    compare.add_argument("--b", required=True, help="Report of the candidate.")
    args = parser.parse_args(argv)

    if args.command == "evaluate":
        report = evaluate(
            args.weights, args.dataset, args.split, args.imgsz, args.confidence, args.limit,
            args.device,
        )
        _print_report(report)
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2))
    else:
        a = json.loads(Path(args.a).read_text())
        b = json.loads(Path(args.b).read_text())
        result = compare_reports(a, b)
        for name in ("precision", "recall", "f1"):
            item = result[name]
            print(
                f"{name:>9}: {item['difference']:+.4f} "
                f"[{item['ci_low']:+.4f}, {item['ci_high']:+.4f}]"
            )
        print(f"P(B better) = {result['probability_b_better']:.3f}")


if __name__ == "__main__":
    main()
