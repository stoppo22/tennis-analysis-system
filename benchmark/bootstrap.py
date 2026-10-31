"""Block-bootstrap confidence intervals for shot-event metrics.

Events inside one rally are correlated, so resampling individual events would
give intervals that are too narrow. Instead, each clip's timeline is split into
fixed-length blocks and whole blocks are resampled with replacement.

Every event is attributed to exactly one block:

- a true positive or false negative belongs to the block of its ground-truth
  time;
- a false positive belongs to the block of its prediction time.

Blocks are identified by ``(clip, block_index)``, so two methods evaluated on
the same clips share the same units and can be compared with a paired
bootstrap.
"""

import math
from collections import defaultdict

import numpy as np

from benchmark.evaluate_events import match_events

DEFAULT_BLOCK_SECONDS = 10.0
DEFAULT_RESAMPLES = 10000
DEFAULT_CONFIDENCE = 0.95

COUNT_COLUMNS = ("true_positives", "false_positives", "false_negatives")


def _block_index(time_seconds, block_seconds):
    if block_seconds is None:
        return 0
    return int(time_seconds // block_seconds)


def count_events_by_block(
    clip_name,
    ground_truth_times,
    predicted_times,
    tolerance_seconds=0.25,
    block_seconds=DEFAULT_BLOCK_SECONDS,
):
    """Return ``{(clip, block): (tp, fp, fn)}`` for one clip.

    ``block_seconds=None`` puts the whole clip in a single block.
    """
    if block_seconds is not None and (
        not math.isfinite(block_seconds) or block_seconds <= 0
    ):
        raise ValueError("Block length must be a positive, finite duration.")

    matches = match_events(
        ground_truth_times,
        predicted_times,
        tolerance_seconds,
    )

    counts = defaultdict(lambda: [0, 0, 0])

    unmatched_ground_truth = sorted(float(t) for t in ground_truth_times)
    unmatched_predictions = sorted(float(t) for t in predicted_times)

    for match in matches:
        block = _block_index(match["ground_truth_time"], block_seconds)
        counts[(clip_name, block)][0] += 1
        unmatched_ground_truth.remove(match["ground_truth_time"])
        unmatched_predictions.remove(match["prediction_time"])

    for time_seconds in unmatched_predictions:
        block = _block_index(time_seconds, block_seconds)
        counts[(clip_name, block)][1] += 1

    for time_seconds in unmatched_ground_truth:
        block = _block_index(time_seconds, block_seconds)
        counts[(clip_name, block)][2] += 1

    return {key: tuple(value) for key, value in counts.items()}


def merge_counts(*count_mappings):
    """Merge per-clip count mappings with disjoint keys."""
    merged = {}
    for mapping in count_mappings:
        overlap = merged.keys() & mapping.keys()
        if overlap:
            raise ValueError(f"Duplicate block keys: {sorted(overlap)[:3]}")
        merged.update(mapping)
    return merged


def metrics_from_totals(true_positives, false_positives, false_negatives):
    """Precision, recall and F1 from event counts (works on arrays too)."""
    tp = np.asarray(true_positives, dtype=float)
    fp = np.asarray(false_positives, dtype=float)
    fn = np.asarray(false_negatives, dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        precision = np.where(tp + fp > 0, tp / (tp + fp), 0.0)
        recall = np.where(tp + fn > 0, tp / (tp + fn), 0.0)
        f1 = np.where(
            2 * tp + fp + fn > 0,
            2 * tp / (2 * tp + fp + fn),
            0.0,
        )
    return precision, recall, f1


def _counts_matrix(counts, keys):
    return np.array(
        [counts.get(key, (0, 0, 0)) for key in keys],
        dtype=float,
    ).reshape(len(keys), 3)


def _interval(samples, confidence):
    alpha = (1.0 - confidence) / 2.0
    low, high = np.quantile(samples, [alpha, 1.0 - alpha])
    return float(low), float(high)


def _validate_bootstrap_arguments(n_resamples, confidence):
    if n_resamples < 1:
        raise ValueError("At least one bootstrap resample is required.")
    if not 0.0 < confidence < 1.0:
        raise ValueError("Confidence must be between 0 and 1.")


def _resample_totals(matrix, n_resamples, seed):
    """Return ``(n_resamples, 3)`` totals from resampling rows with replacement."""
    unit_count = matrix.shape[0]
    if unit_count == 0:
        raise ValueError("Cannot bootstrap an empty benchmark.")

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, unit_count, size=(n_resamples, unit_count))
    return matrix[indices].sum(axis=1)


def bootstrap_metrics(
    counts,
    n_resamples=DEFAULT_RESAMPLES,
    confidence=DEFAULT_CONFIDENCE,
    seed=0,
):
    """Point estimates and bootstrap intervals for one method."""
    _validate_bootstrap_arguments(n_resamples, confidence)
    keys = sorted(counts)
    matrix = _counts_matrix(counts, keys)
    totals = matrix.sum(axis=0)
    point = metrics_from_totals(*totals)

    sampled = _resample_totals(matrix, n_resamples, seed)
    sampled_metrics = metrics_from_totals(
        sampled[:, 0],
        sampled[:, 1],
        sampled[:, 2],
    )

    result = {"units": len(keys)}
    for name, estimate, samples in zip(
        ("precision", "recall", "f1"),
        point,
        sampled_metrics,
    ):
        low, high = _interval(samples, confidence)
        result[name] = {
            "value": float(estimate),
            "ci_low": low,
            "ci_high": high,
        }
    return result


def paired_bootstrap_difference(
    counts_a,
    counts_b,
    n_resamples=DEFAULT_RESAMPLES,
    confidence=DEFAULT_CONFIDENCE,
    seed=0,
):
    """Bootstrap the metric difference ``B - A`` using the same resampled blocks.

    Because both methods are scored on the same resampled units, the interval
    reflects the paired improvement rather than two independent uncertainties.
    ``probability_b_better`` is the fraction of resamples where B's F1 exceeds A's.
    """
    _validate_bootstrap_arguments(n_resamples, confidence)
    keys = sorted(counts_a.keys() | counts_b.keys())
    matrix_a = _counts_matrix(counts_a, keys)
    matrix_b = _counts_matrix(counts_b, keys)

    point_a = metrics_from_totals(*matrix_a.sum(axis=0))
    point_b = metrics_from_totals(*matrix_b.sum(axis=0))

    unit_count = len(keys)
    if unit_count == 0:
        raise ValueError("Cannot bootstrap an empty benchmark.")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, unit_count, size=(n_resamples, unit_count))
    sampled_a = matrix_a[indices].sum(axis=1)
    sampled_b = matrix_b[indices].sum(axis=1)
    metrics_a = metrics_from_totals(
        sampled_a[:, 0],
        sampled_a[:, 1],
        sampled_a[:, 2],
    )
    metrics_b = metrics_from_totals(
        sampled_b[:, 0],
        sampled_b[:, 1],
        sampled_b[:, 2],
    )

    result = {"units": unit_count}
    for position, name in enumerate(("precision", "recall", "f1")):
        differences = metrics_b[position] - metrics_a[position]
        low, high = _interval(differences, confidence)
        result[name] = {
            "difference": float(point_b[position] - point_a[position]),
            "ci_low": low,
            "ci_high": high,
        }
    f1_differences = metrics_b[2] - metrics_a[2]
    result["probability_b_better"] = float(np.mean(f1_differences > 0))
    return result
