import argparse
import csv
import json
import math
from functools import lru_cache


def _validate_times(times, label):
    validated_times = []
    for time_seconds in times:
        value = float(time_seconds)
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{label} times must be finite and non-negative.")
        validated_times.append(value)
    return sorted(validated_times)


def match_events(ground_truth_times, predicted_times, tolerance_seconds=0.25):
    if not math.isfinite(tolerance_seconds) or tolerance_seconds < 0:
        raise ValueError("Tolerance must be finite and non-negative.")

    ground_truth = _validate_times(ground_truth_times, "Ground-truth")
    predictions = _validate_times(predicted_times, "Prediction")

    def total_error(index_pairs):
        return sum(
            abs(ground_truth[ground_truth_index] - predictions[prediction_index])
            for ground_truth_index, prediction_index in index_pairs
        )

    @lru_cache(maxsize=None)
    def find_best_matching(ground_truth_index, prediction_index):
        if (
            ground_truth_index == len(ground_truth)
            or prediction_index == len(predictions)
        ):
            return ()

        candidates = [
            find_best_matching(ground_truth_index + 1, prediction_index),
            find_best_matching(ground_truth_index, prediction_index + 1),
        ]

        error = abs(
            ground_truth[ground_truth_index] - predictions[prediction_index]
        )
        if error <= tolerance_seconds:
            candidates.append(
                ((ground_truth_index, prediction_index),)
                + find_best_matching(ground_truth_index + 1, prediction_index + 1)
            )

        return min(
            candidates,
            key=lambda pairs: (-len(pairs), total_error(pairs), pairs),
        )

    index_pairs = find_best_matching(0, 0)
    return [
        {
            "ground_truth_time": ground_truth[ground_truth_index],
            "prediction_time": predictions[prediction_index],
            "absolute_error": abs(
                ground_truth[ground_truth_index] - predictions[prediction_index]
            ),
        }
        for ground_truth_index, prediction_index in index_pairs
    ]


def evaluate_events(ground_truth_times, predicted_times, tolerance_seconds=0.25):
    ground_truth = _validate_times(ground_truth_times, "Ground-truth")
    predictions = _validate_times(predicted_times, "Prediction")
    matches = match_events(ground_truth, predictions, tolerance_seconds)

    true_positives = len(matches)
    false_positives = len(predictions) - true_positives
    false_negatives = len(ground_truth) - true_positives

    precision = true_positives / len(predictions) if predictions else 0.0
    recall = true_positives / len(ground_truth) if ground_truth else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )
    mean_absolute_timing_error = (
        sum(match["absolute_error"] for match in matches) / true_positives
        if matches
        else None
    )

    return {
        "tolerance_seconds": tolerance_seconds,
        "ground_truth_events": len(ground_truth),
        "predicted_events": len(predictions),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mean_absolute_timing_error": mean_absolute_timing_error,
        "matches": matches,
    }


def load_event_times(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None or "time_seconds" not in reader.fieldnames:
            raise ValueError(f"CSV must contain a time_seconds column: {csv_path}")
        return _validate_times(
            (row["time_seconds"] for row in reader),
            f"Events in {csv_path}",
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate predicted shot events against ground truth."
    )
    parser.add_argument("--ground-truth", required=True, help="Annotation CSV path.")
    parser.add_argument("--predictions", required=True, help="Prediction CSV path.")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.25,
        help="Maximum matching distance in seconds (default: 0.25).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    metrics = evaluate_events(
        load_event_times(args.ground_truth),
        load_event_times(args.predictions),
        tolerance_seconds=args.tolerance,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
