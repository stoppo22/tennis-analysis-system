"""Leave-one-clip-out comparison of shot-detection methods.

See ``EXPERIMENT_swing_detector.md`` for the protocol this implements.

    python -m benchmark.loco_experiment --json benchmark/results/swing_vs_persistence.json
"""

import argparse
import csv
import itertools
import json
from pathlib import Path

from benchmark.bootstrap import (
    DEFAULT_BLOCK_SECONDS,
    bootstrap_metrics,
    count_events_by_block,
    metrics_from_totals,
    merge_counts,
    paired_bootstrap_difference,
)
from benchmark.detections import load_detections_csv
from benchmark.evaluate_events import evaluate_events, load_event_times
from utils.shot_detection_utils import (
    DEFAULT_SMOOTHING_SECONDS,
    detect_shot_frames,
    interpolate_ball_positions,
)
from utils.swing_shot_detection import detect_swing_shot_frames

BENCHMARK_DIRECTORY = Path(__file__).resolve().parent
TOLERANCE_SECONDS = 0.25
NEAR_BEST_MARGIN = 0.05

PERSISTENCE_GRID = [0.52, 0.60, 0.68, 0.72, 0.80, 0.88, 1.00]
SWING_RATIOS = [0.06, 0.08, 0.10, 0.12, 0.15, 0.18, 0.22, 0.26]
SWING_SMOOTHING = [0.08, 0.12, 0.20, 0.28]

# Exploratory follow-up: the pre-registered search selected the largest ratio
# and smoothing on every fold, so the optimum may lie beyond the grid edge.
EXTENDED_SWING_RATIOS = [0.06, 0.08, 0.10, 0.12, 0.15, 0.18, 0.22, 0.26,
                         0.30, 0.35, 0.40, 0.45, 0.50]
EXTENDED_SWING_SMOOTHING = [0.08, 0.12, 0.20, 0.28, 0.36, 0.44, 0.52]


def _run_persistence(positions, fps, params):
    (persistence_seconds,) = params
    return detect_shot_frames(
        positions,
        fps,
        persistence_seconds=persistence_seconds,
        smoothing_seconds=DEFAULT_SMOOTHING_SECONDS,
    )


def _run_swing(positions, fps, params):
    ratio, smoothing_seconds = params
    return detect_swing_shot_frames(
        positions,
        fps,
        min_swing_ratio=ratio,
        smoothing_seconds=smoothing_seconds,
    )


METHODS = {
    "persistence": {
        "run": _run_persistence,
        "grid": [(seconds,) for seconds in PERSISTENCE_GRID],
        "parameter_names": ("persistence_seconds",),
    },
    "swing": {
        "run": _run_swing,
        "grid": list(itertools.product(SWING_RATIOS, SWING_SMOOTHING)),
        "parameter_names": ("min_swing_ratio", "smoothing_seconds"),
    },
}


def use_extended_grid():
    METHODS["swing"]["grid"] = list(
        itertools.product(EXTENDED_SWING_RATIOS, EXTENDED_SWING_SMOOTHING)
    )


def load_clip_data(sources_path, detections_directory, annotations_directory):
    clips = {}
    with Path(sources_path).open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            clip = row["clip"]
            detections_path = Path(detections_directory) / f"{clip}.csv"
            if not detections_path.is_file():
                continue
            fps = float(row["fps"])
            clips[clip] = {
                "fps": fps,
                "positions": interpolate_ball_positions(
                    load_detections_csv(detections_path)
                ),
                "ground_truth": load_event_times(
                    Path(annotations_directory) / f"{clip}.csv"
                ),
            }
    if len(clips) < 2:
        raise ValueError("Leave-one-clip-out evaluation needs at least two clips.")
    return clips


def evaluate_configuration(method, params, clip_data):
    """Return event times and (tp, fp, fn) for one configuration on one clip."""
    frames = METHODS[method]["run"](clip_data["positions"], clip_data["fps"], params)
    times = [int(frame) / clip_data["fps"] for frame in frames]
    metrics = evaluate_events(clip_data["ground_truth"], times, TOLERANCE_SECONDS)
    counts = (
        metrics["true_positives"],
        metrics["false_positives"],
        metrics["false_negatives"],
    )
    return times, counts


def selection_key(params, f1):
    """Highest F1, ties broken toward larger (more conservative) parameters."""
    return (round(f1, 12),) + tuple(params)


def run_experiment(clips, block_seconds, resamples, seed):
    cache = {}  # (method, params, clip) -> (times, counts)
    for method, spec in METHODS.items():
        for params in spec["grid"]:
            for clip, data in clips.items():
                cache[(method, params, clip)] = evaluate_configuration(
                    method, params, data
                )

    def f1_for(method, params, clip_names):
        totals = [
            sum(cache[(method, params, clip)][1][i] for clip in clip_names)
            for i in range(3)
        ]
        return float(metrics_from_totals(*totals)[2])

    results = {"clips": list(clips), "methods": {}}
    block_counts = {}

    for method, spec in METHODS.items():
        folds = {}
        per_clip_counts = []
        for held_out in clips:
            training = [clip for clip in clips if clip != held_out]
            best = max(
                spec["grid"],
                key=lambda params: selection_key(
                    params, f1_for(method, params, training)
                ),
            )
            times, counts = cache[(method, best, held_out)]
            folds[held_out] = {
                "selected": dict(zip(spec["parameter_names"], best)),
                "training_f1": f1_for(method, best, training),
                "held_out_counts": dict(
                    zip(("tp", "fp", "fn"), counts)
                ),
                "held_out_f1": f1_for(method, best, [held_out]),
            }
            per_clip_counts.append(
                count_events_by_block(
                    held_out,
                    clips[held_out]["ground_truth"],
                    times,
                    TOLERANCE_SECONDS,
                    block_seconds,
                )
            )

        counts = merge_counts(*per_clip_counts)
        block_counts[method] = counts
        results["methods"][method] = {
            "loco_folds": folds,
            "loco_overall": bootstrap_metrics(counts, resamples, seed=seed),
            "oracle_best_per_clip": {
                clip: _oracle(method, spec, clip, f1_for) for clip in clips
            },
            "sensitivity": _sensitivity(method, spec, clips, f1_for),
        }

    results["comparison_swing_minus_persistence"] = paired_bootstrap_difference(
        block_counts["persistence"],
        block_counts["swing"],
        resamples,
        seed=seed,
    )
    results["configurations_evaluated"] = sum(
        len(spec["grid"]) for spec in METHODS.values()
    )
    results["settings"] = {
        "tolerance_seconds": TOLERANCE_SECONDS,
        "block_seconds": block_seconds,
        "resamples": resamples,
        "seed": seed,
    }
    return results


def _oracle(method, spec, clip, f1_for):
    best = max(
        spec["grid"], key=lambda params: selection_key(params, f1_for(method, params, [clip]))
    )
    return {
        "parameters": dict(zip(spec["parameter_names"], best)),
        "f1": f1_for(method, best, [clip]),
    }


def _sensitivity(method, spec, clips, f1_for):
    """Fraction of the grid within the margin of the best F1 on every clip."""
    per_clip_best = {
        clip: max(f1_for(method, params, [clip]) for params in spec["grid"])
        for clip in clips
    }
    robust = [
        params
        for params in spec["grid"]
        if all(
            f1_for(method, params, [clip]) >= per_clip_best[clip] - NEAR_BEST_MARGIN
            for clip in clips
        )
    ]
    return {
        "near_best_on_every_clip": len(robust),
        "grid_size": len(spec["grid"]),
        "fraction": len(robust) / len(spec["grid"]),
        "configs": [dict(zip(spec["parameter_names"], p)) for p in robust],
    }


def print_results(results):
    print(f"Clips: {', '.join(results['clips'])}")
    print(f"Configurations evaluated: {results['configurations_evaluated']}\n")
    for method, summary in results["methods"].items():
        print(f"== {method} (leave-one-clip-out) ==")
        for clip, fold in summary["loco_folds"].items():
            c = fold["held_out_counts"]
            print(
                f"  held out {clip[:38]:38} params={fold['selected']} "
                f"train F1={fold['training_f1']:.3f} -> held-out F1={fold['held_out_f1']:.3f} "
                f"(TP {c['tp']}, FP {c['fp']}, FN {c['fn']})"
            )
        for name in ("precision", "recall", "f1"):
            m = summary["loco_overall"][name]
            print(f"  {name:>9}: {m['value']:.4f} [{m['ci_low']:.4f}, {m['ci_high']:.4f}]")
        s = summary["sensitivity"]
        print(
            f"  oracle (in-sample best): "
            + ", ".join(f"{v['f1']:.3f}" for v in summary["oracle_best_per_clip"].values())
            + f" | near-best on every clip: {s['near_best_on_every_clip']}/{s['grid_size']}\n"
        )
    comparison = results["comparison_swing_minus_persistence"]
    print("== swing minus persistence (paired, held-out predictions) ==")
    for name in ("precision", "recall", "f1"):
        d = comparison[name]
        print(f"  {name:>9}: {d['difference']:+.4f} [{d['ci_low']:+.4f}, {d['ci_high']:+.4f}]")
    print(f"  P(swing F1 > persistence F1): {comparison['probability_b_better']:.3f}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default=BENCHMARK_DIRECTORY / "sources.csv")
    parser.add_argument("--detections", default=BENCHMARK_DIRECTORY / "detections")
    parser.add_argument("--annotations", default=BENCHMARK_DIRECTORY / "annotations")
    parser.add_argument("--block-seconds", type=float, default=DEFAULT_BLOCK_SECONDS)
    parser.add_argument("--resamples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", help="Write the full results to this path.")
    parser.add_argument(
        "--extended-grid",
        action="store_true",
        help="Exploratory: search beyond the pre-registered swing grid.",
    )
    args = parser.parse_args(argv)
    if args.extended_grid:
        use_extended_grid()

    clips = load_clip_data(args.sources, args.detections, args.annotations)
    results = run_experiment(clips, args.block_seconds, args.resamples, args.seed)
    print_results(results)
    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
