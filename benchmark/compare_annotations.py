"""Measure how well two independent annotations of the same clip agree.

Annotating each test clip twice, on different days, quantifies the noise in the
ground truth itself. The F1 between the two annotations is a realistic upper bound
for any detector scored against either one: a method cannot reasonably be expected
to agree with a reference more closely than two careful humans agree with each
other.

    python -m benchmark.compare_annotations --first a.csv --second b.csv
    python -m benchmark.compare_annotations --first dir_one --second dir_two

When directories are given, files with the same name are compared and the counts
are pooled.
"""

import argparse
import json
from pathlib import Path

from benchmark.evaluate_events import (
    evaluate_events,
    load_event_times,
    match_events,
)

DEFAULT_TOLERANCE_SECONDS = 0.25


def compare_annotations(first_times, second_times, tolerance_seconds=DEFAULT_TOLERANCE_SECONDS):
    """Agreement between two lists of event times (seconds).

    Counts use the first annotation as reference: ``only_first`` events were not
    marked in the second annotation, ``only_second`` events were not marked in the
    first. The F1 is symmetric, so which annotation is "first" does not change it.
    """
    metrics = evaluate_events(first_times, second_times, tolerance_seconds)
    matches = match_events(first_times, second_times, tolerance_seconds)

    signed_differences = [
        match["prediction_time"] - match["ground_truth_time"] for match in matches
    ]
    matched_first = {match["ground_truth_time"] for match in matches}
    matched_second = {match["prediction_time"] for match in matches}

    return {
        "tolerance_seconds": tolerance_seconds,
        "events_first": len(first_times),
        "events_second": len(second_times),
        "matched": metrics["true_positives"],
        "only_first": metrics["false_negatives"],
        "only_second": metrics["false_positives"],
        "agreement_f1": metrics["f1"],
        "mean_absolute_difference_seconds": metrics["mean_absolute_timing_error"],
        "mean_signed_difference_seconds": (
            sum(signed_differences) / len(signed_differences)
            if signed_differences
            else None
        ),
        "max_absolute_difference_seconds": (
            max(abs(value) for value in signed_differences)
            if signed_differences
            else None
        ),
        "unmatched_first_times": [
            time for time in first_times if time not in matched_first
        ],
        "unmatched_second_times": [
            time for time in second_times if time not in matched_second
        ],
    }


def pooled_agreement(per_clip):
    """Pooled F1 over several clips from their match/unmatched counts."""
    matched = sum(item["matched"] for item in per_clip.values())
    only_first = sum(item["only_first"] for item in per_clip.values())
    only_second = sum(item["only_second"] for item in per_clip.values())
    denominator = 2 * matched + only_first + only_second
    return {
        "clips": len(per_clip),
        "matched": matched,
        "only_first": only_first,
        "only_second": only_second,
        "agreement_f1": 2 * matched / denominator if denominator else 0.0,
    }


def collect_pairs(first, second):
    """``{name: (first_path, second_path)}`` for two files or two directories."""
    first, second = Path(first), Path(second)
    if first.is_dir() != second.is_dir():
        raise ValueError("Pass either two files or two directories.")
    if not first.is_dir():
        return {first.stem: (first, second)}

    names = sorted(path.name for path in first.glob("*.csv"))
    pairs = {
        Path(name).stem: (first / name, second / name)
        for name in names
        if (second / name).is_file()
    }
    if not pairs:
        raise ValueError("No annotation files with the same name in both directories.")
    return pairs


def print_report(per_clip, pooled):
    for name, item in per_clip.items():
        timing = item["mean_absolute_difference_seconds"]
        bias = item["mean_signed_difference_seconds"]
        print(
            f"{name}: agreement F1 {item['agreement_f1']:.4f} "
            f"(matched {item['matched']}, only first {item['only_first']}, "
            f"only second {item['only_second']})"
        )
        if timing is not None:
            print(
                f"    timing: mean |difference| {timing:.4f} s, "
                f"mean signed {bias:+.4f} s, max {item['max_absolute_difference_seconds']:.4f} s"
            )
    if len(per_clip) > 1:
        print(
            f"\npooled over {pooled['clips']} clips: agreement F1 "
            f"{pooled['agreement_f1']:.4f} (matched {pooled['matched']}, "
            f"only first {pooled['only_first']}, only second {pooled['only_second']})"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--first", required=True, help="First annotation CSV or directory.")
    parser.add_argument("--second", required=True, help="Second annotation CSV or directory.")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE_SECONDS)
    parser.add_argument("--json", help="Write the full results to this path.")
    args = parser.parse_args(argv)

    per_clip = {
        name: compare_annotations(
            load_event_times(first_path),
            load_event_times(second_path),
            args.tolerance,
        )
        for name, (first_path, second_path) in collect_pairs(args.first, args.second).items()
    }
    pooled = pooled_agreement(per_clip)
    print_report(per_clip, pooled)

    if args.json:
        Path(args.json).write_text(
            json.dumps({"per_clip": per_clip, "pooled": pooled}, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
