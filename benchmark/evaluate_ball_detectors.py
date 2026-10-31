"""Compare ball detectors on annotated frames, with confidence intervals.

Each detector is a directory of detection CSVs (``<clip>.csv``, the format of
``benchmark/detections/``). Ball annotations are read from
``<annotations>/<clip>.csv`` (see ``benchmark.ball_detection``).

    python -m benchmark.evaluate_ball_detectors \
        --detectors yolo11l=benchmark/detections yolo26l=runs/yolo26l/detections \
        --annotations benchmark/ball_annotations

With two or more detectors, the second is compared with the first by a paired
bootstrap over the annotated frames.
"""

import argparse
import json
from pathlib import Path

from benchmark.ball_detection import (
    DEFAULT_MAX_DISTANCE_PIXELS,
    evaluate_ball_detections,
    load_ball_annotations,
    median,
)
from benchmark.bootstrap import (
    DEFAULT_CONFIDENCE,
    DEFAULT_RESAMPLES,
    bootstrap_metrics,
    merge_counts,
    paired_bootstrap_difference,
)
from benchmark.detections import load_detections_csv


def evaluate_detector(detections_directory, annotations_directory, max_distance):
    all_counts, all_errors, per_clip = [], [], {}
    annotation_paths = sorted(Path(annotations_directory).glob("*.csv"))
    if not annotation_paths:
        raise ValueError(f"No ball annotations in {annotations_directory}.")

    for annotation_path in annotation_paths:
        clip = annotation_path.stem
        detections_path = Path(detections_directory) / f"{clip}.csv"
        if not detections_path.is_file():
            raise FileNotFoundError(f"Missing detections: {detections_path}")
        counts, errors = evaluate_ball_detections(
            clip,
            load_ball_annotations(annotation_path),
            load_detections_csv(detections_path),
            max_distance,
        )
        all_counts.append(counts)
        all_errors.extend(errors)
        per_clip[clip] = {
            "frames": len(counts),
            "tp": sum(c[0] for c in counts.values()),
            "fp": sum(c[1] for c in counts.values()),
            "fn": sum(c[2] for c in counts.values()),
        }
    return merge_counts(*all_counts), all_errors, per_clip


def parse_detector(text):
    name, separator, directory = text.partition("=")
    if not separator or not name or not directory:
        raise argparse.ArgumentTypeError("Use NAME=DIRECTORY.")
    return name, directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--detectors", nargs="+", type=parse_detector, required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--max-distance", type=float, default=DEFAULT_MAX_DISTANCE_PIXELS)
    parser.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", help="Write the results to this path.")
    args = parser.parse_args(argv)

    results, counts_by_detector = {}, {}
    for name, directory in args.detectors:
        counts, errors, per_clip = evaluate_detector(
            directory, args.annotations, args.max_distance
        )
        counts_by_detector[name] = counts
        summary = bootstrap_metrics(counts, args.resamples, args.confidence, args.seed)
        summary["median_error_pixels"] = median(errors)
        summary["per_clip"] = per_clip
        results[name] = summary

        print(f"== {name} ({len(counts)} annotated frames, ≤ {args.max_distance:g} px) ==")
        for metric in ("precision", "recall", "f1"):
            item = summary[metric]
            print(f"  {metric:>9}: {item['value']:.4f} [{item['ci_low']:.4f}, {item['ci_high']:.4f}]")
        if summary["median_error_pixels"] is not None:
            print(f"  median localisation error: {summary['median_error_pixels']:.1f} px")

    if len(args.detectors) >= 2:
        first, second = args.detectors[0][0], args.detectors[1][0]
        comparison = paired_bootstrap_difference(
            counts_by_detector[first],
            counts_by_detector[second],
            args.resamples,
            args.confidence,
            args.seed,
        )
        results["comparison"] = {"baseline": first, "candidate": second, **comparison}
        print(f"\n== {second} minus {first} (paired) ==")
        for metric in ("precision", "recall", "f1"):
            item = comparison[metric]
            print(f"  {metric:>9}: {item['difference']:+.4f} [{item['ci_low']:+.4f}, {item['ci_high']:+.4f}]")

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
