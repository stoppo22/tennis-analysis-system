"""Evaluate one or more shot-detection methods on every clip in the benchmark.

Clips and their splits come from ``benchmark/sources.csv``. For each clip the
ground truth is read from ``<annotations>/<clip>.csv`` and each method's
predictions from ``<predictions>/<clip>_<method>.csv``. For historical files
the ``_rally_NN`` suffix of the clip name may be omitted from the prediction
file name.

Example:
    python -m benchmark.run_benchmark --methods baseline persistence_18
"""

import argparse
import csv
import json
import re
from pathlib import Path

from benchmark.bootstrap import (
    DEFAULT_BLOCK_SECONDS,
    DEFAULT_CONFIDENCE,
    DEFAULT_RESAMPLES,
    bootstrap_metrics,
    count_events_by_block,
    merge_counts,
    paired_bootstrap_difference,
)
from benchmark.evaluate_events import evaluate_events, load_event_times

BENCHMARK_DIRECTORY = Path(__file__).resolve().parent
RALLY_SUFFIX = re.compile(r"_rally_\d+$")


def load_clips(sources_path, splits=None):
    """Return ``[(clip, split)]`` from the sources manifest."""
    with Path(sources_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {"clip", "split"}
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError(f"{sources_path} must contain columns {sorted(required)}.")
        # A blank "events" cell marks a clip that is not annotated yet; it is
        # skipped here and counted by ``count_pending_clips``.
        clips = [
            (row["clip"], row["split"])
            for row in reader
            if row.get("events", "x").strip() != ""
        ]

    if splits:
        clips = [(clip, split) for clip, split in clips if split in splits]
    if not clips:
        raise ValueError("No clips match the requested splits.")
    return clips


def count_pending_clips(sources_path, splits=None):
    """Number of clips in the manifest that are not annotated yet."""
    with Path(sources_path).open(newline="", encoding="utf-8") as csv_file:
        return sum(
            1
            for row in csv.DictReader(csv_file)
            if row.get("events", "x").strip() == ""
            and (not splits or row["split"] in splits)
        )


def find_predictions_path(predictions_directory, clip, method):
    candidates = [
        Path(predictions_directory) / f"{clip}_{method}.csv",
        Path(predictions_directory) / f"{RALLY_SUFFIX.sub('', clip)}_{method}.csv",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(
        f"No predictions for method '{method}' on clip '{clip}'. Looked for: {searched}"
    )


def evaluate_method(
    clips,
    method,
    annotations_directory,
    predictions_directory,
    tolerance_seconds,
    block_seconds,
):
    """Evaluate one method; return per-clip metrics and block counts."""
    per_clip = {}
    block_counts = []

    for clip, split in clips:
        annotation_path = Path(annotations_directory) / f"{clip}.csv"
        if not annotation_path.is_file():
            raise FileNotFoundError(f"Missing annotations: {annotation_path}")

        ground_truth = load_event_times(annotation_path)
        predictions = load_event_times(
            find_predictions_path(predictions_directory, clip, method)
        )

        metrics = evaluate_events(ground_truth, predictions, tolerance_seconds)
        metrics.pop("matches")
        metrics["split"] = split
        per_clip[clip] = metrics

        block_counts.append(
            count_events_by_block(
                clip,
                ground_truth,
                predictions,
                tolerance_seconds,
                block_seconds,
            )
        )

    return per_clip, merge_counts(*block_counts)


def format_interval(summary):
    return f"{summary['value']:.4f} [{summary['ci_low']:.4f}, {summary['ci_high']:.4f}]"


def build_report(args):
    clips = load_clips(args.sources, args.splits)
    report = {
        "clips": [clip for clip, _ in clips],
        "tolerance_seconds": args.tolerance,
        "block_seconds": args.block_seconds,
        "resamples": args.resamples,
        "confidence": args.confidence,
        "seed": args.seed,
        "pending_clips": count_pending_clips(args.sources, args.splits),
        "methods": {},
    }
    counts_by_method = {}

    for method in args.methods:
        per_clip, counts = evaluate_method(
            clips,
            method,
            args.annotations,
            args.predictions,
            args.tolerance,
            args.block_seconds,
        )
        counts_by_method[method] = counts
        report["methods"][method] = {
            "per_clip": per_clip,
            "overall": bootstrap_metrics(
                counts,
                args.resamples,
                args.confidence,
                args.seed,
            ),
            "events": {
                "ground_truth": sum(c["ground_truth_events"] for c in per_clip.values()),
                "true_positives": sum(c["true_positives"] for c in per_clip.values()),
                "false_positives": sum(c["false_positives"] for c in per_clip.values()),
                "false_negatives": sum(c["false_negatives"] for c in per_clip.values()),
            },
        }

    if len(args.methods) >= 2:
        baseline, candidate = args.methods[0], args.methods[1]
        report["comparison"] = {
            "baseline": baseline,
            "candidate": candidate,
            **paired_bootstrap_difference(
                counts_by_method[baseline],
                counts_by_method[candidate],
                args.resamples,
                args.confidence,
                args.seed,
            ),
        }

    return report


def print_report(report):
    percent = int(report["confidence"] * 100)
    block = report["block_seconds"]
    print(
        f"Clips: {len(report['clips'])} | tolerance ±{report['tolerance_seconds']} s | "
        f"{percent}% block-bootstrap CI "
        f"({'whole clip' if block is None else f'{block:g} s blocks'}, "
        f"{report['resamples']} resamples, seed {report['seed']})"
    )

    if report["pending_clips"]:
        print(f"({report['pending_clips']} clips are pending annotation and are not included)")

    for method, result in report["methods"].items():
        events = result["events"]
        print(f"\n== {method} ==")
        print(
            f"events: {events['ground_truth']} ground truth, "
            f"TP {events['true_positives']}, FP {events['false_positives']}, "
            f"FN {events['false_negatives']}"
        )
        for name in ("precision", "recall", "f1"):
            print(f"{name:>9}: {format_interval(result['overall'][name])}")
        print("  per clip:")
        for clip, metrics in result["per_clip"].items():
            print(
                f"    [{metrics['split']}] {clip}: F1 {metrics['f1']:.4f} "
                f"(TP {metrics['true_positives']}, FP {metrics['false_positives']}, "
                f"FN {metrics['false_negatives']})"
            )

    comparison = report.get("comparison")
    if comparison:
        print(f"\n== {comparison['candidate']} minus {comparison['baseline']} (paired) ==")
        for name in ("precision", "recall", "f1"):
            item = comparison[name]
            print(
                f"{name:>9}: {item['difference']:+.4f} "
                f"[{item['ci_low']:+.4f}, {item['ci_high']:+.4f}]"
            )
        print(
            "P(candidate F1 > baseline F1) across resamples: "
            f"{comparison['probability_b_better']:.3f}"
        )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Evaluate shot-detection methods across the whole benchmark."
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        required=True,
        help="Method names; with two or more, the second is compared to the first.",
    )
    parser.add_argument("--splits", nargs="+", help="Only use these splits.")
    parser.add_argument("--sources", default=BENCHMARK_DIRECTORY / "sources.csv")
    parser.add_argument("--annotations", default=BENCHMARK_DIRECTORY / "annotations")
    parser.add_argument("--predictions", default=BENCHMARK_DIRECTORY / "predictions")
    parser.add_argument("--tolerance", type=float, default=0.25)
    parser.add_argument(
        "--block-seconds",
        type=float,
        default=DEFAULT_BLOCK_SECONDS,
        help="Bootstrap block length; use 0 to resample whole clips.",
    )
    parser.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", help="Also write the full report to this path.")
    args = parser.parse_args(argv)
    if args.block_seconds == 0:
        args.block_seconds = None
    return args


def main(argv=None):
    args = parse_args(argv)
    report = build_report(args)
    print_report(report)
    if args.json:
        Path(args.json).write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
