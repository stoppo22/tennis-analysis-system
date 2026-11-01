"""Filters applied to raw ball detections before event detection.

The ball model sometimes locks onto a fixed mark on the court (for example the
smudge left by a bounce on clay) and reports it in many frames. A real ball cannot
stay inside a few pixels for a second, so such detections can be removed without any
labels.
"""

import math

import numpy as np

DEFAULT_RADIUS_FRACTION = 0.012  # of the frame width: about 23 px at 1920 px
DEFAULT_MIN_SECONDS = 1.0


def _centers(detections):
    indices, centers = [], []
    for index, entry in enumerate(detections):
        box = entry.get(1) if entry else None
        if box:
            indices.append(index)
            centers.append(((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0))
    return indices, np.asarray(centers, dtype=float).reshape(-1, 2)


def suppress_static_detections(
    detections,
    fps,
    frame_width,
    radius_fraction=DEFAULT_RADIUS_FRACTION,
    min_seconds=DEFAULT_MIN_SECONDS,
):
    """Drop detections that stay in the same place for at least ``min_seconds``.

    A detection is static if at least ``ceil(min_seconds * fps)`` detections of the
    clip, itself included, have their centre within ``radius_fraction * frame_width``
    pixels of its own centre. Static detections are replaced by empty entries, so the
    result has the same length and frame numbering as the input; the input is not
    modified. Returns ``(filtered_detections, removed_count)``.
    """
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("FPS must be a finite number greater than zero.")
    if frame_width <= 0 or radius_fraction <= 0 or min_seconds <= 0:
        raise ValueError("Frame width, radius and duration must be positive.")

    indices, centers = _centers(detections)
    filtered = [dict(entry) if entry else {} for entry in detections]
    if not len(indices):
        return filtered, 0

    radius = radius_fraction * frame_width
    needed = math.ceil(min_seconds * fps)
    distances = np.hypot(
        centers[:, None, 0] - centers[None, :, 0],
        centers[:, None, 1] - centers[None, :, 1],
    )
    neighbours = (distances <= radius).sum(axis=1)

    removed = 0
    for index, count in zip(indices, neighbours):
        if count >= needed:
            filtered[index] = {}
            removed += 1
    return filtered, removed
