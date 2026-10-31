"""Direct evaluation of ball detections against annotated ball positions.

Shot-event F1 measures the ball detector only indirectly. This module scores the
detections themselves on a random sample of frames where a human marked either the
ball centre or "not visible".

Annotation CSV columns: ``frame,x,y,visible`` (``visible`` is 1 or 0; ``x`` and
``y`` are empty when the ball is not visible).

For every annotated frame:

- ball visible and a detection centred within ``max_distance`` pixels: true positive;
- ball visible and a detection farther away: false positive and false negative
  (a wrong detection hides the missing one);
- ball visible and no detection: false negative;
- ball not visible and a detection: false positive.

The per-frame outcomes are returned as ``{(clip, frame): (tp, fp, fn)}`` so that
they can be passed to the bootstrap functions in ``benchmark.bootstrap``.
"""

import csv
import math
import random
from pathlib import Path

DEFAULT_MAX_DISTANCE_PIXELS = 12.0  # for 1280-pixel-wide frames; scale for other sizes
ANNOTATION_FIELDS = ["frame", "x", "y", "visible"]


def sample_frames(frame_count, count, seed, min_gap=10):
    """Seeded random frames, sorted, at least ``min_gap`` apart."""
    if count < 1 or min_gap < 1:
        raise ValueError("Need a positive sample size and gap.")
    candidates = list(range(frame_count))
    random.Random(seed).shuffle(candidates)

    chosen = []
    for frame in candidates:
        if all(abs(frame - other) >= min_gap for other in chosen):
            chosen.append(frame)
            if len(chosen) == count:
                return sorted(chosen)
    raise ValueError("The video is too short for this many well-spaced frames.")


def save_ball_annotations(path, annotations):
    """Write ``{frame: (x, y) | None}``; ``None`` means the ball is not visible."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(ANNOTATION_FIELDS)
        for frame in sorted(annotations):
            position = annotations[frame]
            if position is None:
                writer.writerow([frame, "", "", 0])
            else:
                writer.writerow([frame, f"{position[0]:.1f}", f"{position[1]:.1f}", 1])


def load_ball_annotations(path):
    annotations = {}
    with open(path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != ANNOTATION_FIELDS:
            raise ValueError(f"{path} must have columns {ANNOTATION_FIELDS}.")
        for row in reader:
            frame = int(row["frame"])
            if frame in annotations:
                raise ValueError(f"{path}: frame {frame} annotated twice.")
            if row["visible"] == "1":
                annotations[frame] = (float(row["x"]), float(row["y"]))
            elif row["visible"] == "0":
                annotations[frame] = None
            else:
                raise ValueError(f"{path}: 'visible' must be 0 or 1 (frame {frame}).")
    return annotations


def _box_center(box):
    return (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0


def score_frame(annotation, detection, max_distance):
    """Return ``((tp, fp, fn), error_pixels | None)`` for one annotated frame."""
    box = detection.get(1) if detection else None
    has_detection = bool(box)

    if annotation is None:
        return ((0, 1, 0) if has_detection else (0, 0, 0)), None
    if not has_detection:
        return (0, 0, 1), None

    center_x, center_y = _box_center(box)
    error = math.hypot(center_x - annotation[0], center_y - annotation[1])
    if error <= max_distance:
        return (1, 0, 0), error
    return (0, 1, 1), error


def evaluate_ball_detections(
    clip,
    annotations,
    detections,
    max_distance=DEFAULT_MAX_DISTANCE_PIXELS,
):
    """Score detections on the annotated frames of one clip.

    Returns ``(counts, errors)``: per-frame outcomes keyed by ``(clip, frame)`` and
    the localisation errors (pixels) of the true positives.
    """
    if max_distance <= 0:
        raise ValueError("The distance threshold must be positive.")

    counts, errors = {}, []
    for frame, annotation in annotations.items():
        if not 0 <= frame < len(detections):
            raise ValueError(f"Annotated frame {frame} is outside the detections.")
        outcome, error = score_frame(annotation, detections[frame], max_distance)
        counts[(clip, frame)] = outcome
        if outcome[0] and error is not None:
            errors.append(error)
    return counts, errors


def median(values):
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0
