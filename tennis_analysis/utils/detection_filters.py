"""Filters applied to raw ball detections before event detection.

The ball model sometimes locks onto a fixed mark on the court (for example the
smudge left by a bounce on clay) and reports it in many frames. A real ball cannot
stay inside a few pixels for a second, so such detections can be removed without any
labels.

Another failure is a detection that appears for a frame or two far away from the
rest of the trajectory (a shoe, a logo, a line judge). A ball cannot cross a large part
of the frame between two nearby frames, so such isolated jumps can be removed too.
"""

import math

import numpy as np

DEFAULT_RADIUS_FRACTION = 0.012  # of the frame width: about 23 px at 1920 px
DEFAULT_MIN_SECONDS = 1.0
DEFAULT_MAX_SPEED_FRACTION = 3.0  # frame widths per second: about 240 km/h near the baseline
DEFAULT_MAX_GAP_SECONDS = 0.4


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


def suppress_implausible_jumps(
    detections,
    fps,
    frame_width,
    max_speed_fraction=DEFAULT_MAX_SPEED_FRACTION,
    max_gap_seconds=DEFAULT_MAX_GAP_SECONDS,
):
    """Drop detections that no nearby detection can reach at a plausible speed.

    For each detection the previous and the next detection of the clip are looked at,
    if they are at most ``max_gap_seconds`` away. A neighbour is consistent if the
    distance between the two centres is at most ``max_speed_fraction * frame_width``
    pixels per second times the time between them. A detection that has at least one
    neighbour in range but none that is consistent is removed. A detection with no
    neighbour in range cannot be judged and is kept, and so are two adjacent false
    detections that agree with each other.

    Removed detections are replaced by empty entries, so the result has the same length
    and frame numbering as the input; the input is not modified. Returns
    ``(filtered_detections, removed_count)``.
    """
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("FPS must be a finite number greater than zero.")
    if frame_width <= 0 or max_speed_fraction <= 0 or max_gap_seconds <= 0:
        raise ValueError("Frame width, speed and gap must be positive.")

    indices, centers = _centers(detections)
    filtered = [dict(entry) if entry else {} for entry in detections]
    speed_limit = max_speed_fraction * frame_width  # pixels per second
    max_gap_frames = max_gap_seconds * fps

    removed = 0
    for position, index in enumerate(indices):
        neighbours = [
            other
            for other in (position - 1, position + 1)
            if 0 <= other < len(indices) and abs(indices[other] - index) <= max_gap_frames
        ]
        if not neighbours:
            continue
        reachable = any(
            math.hypot(*(centers[other] - centers[position]))
            <= speed_limit * abs(indices[other] - index) / fps
            for other in neighbours
        )
        if not reachable:
            filtered[index] = {}
            removed += 1
    return filtered, removed
