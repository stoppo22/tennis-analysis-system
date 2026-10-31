"""Shot detection from alternating swings of the ball's vertical position.

In a rally filmed from behind a baseline, the ball's image ``y`` coordinate
rises and falls between the two players: each hit is a local extremum of ``y``
and consecutive hits alternate between maxima (near player) and minima (far
player). Bounces create smaller wiggles in between.

The detector smooths ``y`` with a centred window and runs a ZigZag filter: a
reversal is accepted only when the ball has moved at least ``min_swing_ratio``
times the clip's typical vertical range away from the last extremum. The
accepted extrema alternate by construction and are returned as shot frames.

Unlike the direction-persistence rule in ``shot_detection_utils`` it
(1) uses amplitude instead of a fixed duration, (2) localises the event at the
extremum with no smoothing lag, and (3) enforces alternation.
"""

import numpy as np

from utils.shot_detection_utils import duration_to_odd_frames

DEFAULT_MIN_SWING_RATIO = 0.10
DEFAULT_SWING_SMOOTHING_SECONDS = 0.12
RANGE_PERCENTILES = (5, 95)


def _centered_moving_average(values, window):
    if window <= 1:
        return values.astype(float)
    half = window // 2
    padded = np.pad(values.astype(float), half, mode="edge")
    kernel = np.ones(window) / window
    return np.convolve(padded, kernel, mode="valid")


def _ball_center_y(ball_positions):
    boxes = [position.get(1) for position in ball_positions]
    if any(box is None or len(box) != 4 for box in boxes):
        raise ValueError("Ball positions must be interpolated before detection.")
    boxes = np.asarray(boxes, dtype=float)
    return (boxes[:, 1] + boxes[:, 3]) / 2.0


def zigzag_pivots(values, threshold):
    """Return indices of alternating extrema that swing at least ``threshold``.

    The first and last samples are never returned: they are artefacts of where
    the clip starts and ends, not confirmed reversals.
    """
    if threshold <= 0:
        raise ValueError("Swing threshold must be positive.")

    pivots = []
    direction = 0  # +1 tracking a maximum, -1 tracking a minimum
    low_index = high_index = 0

    extreme_index = 0
    for index in range(1, len(values)):
        value = values[index]

        if direction == 0:
            if value > values[high_index]:
                high_index = index
            if value < values[low_index]:
                low_index = index
            if value - values[low_index] >= threshold:
                pivots.append(low_index)
                direction, extreme_index = 1, index
            elif values[high_index] - value >= threshold:
                pivots.append(high_index)
                direction, extreme_index = -1, index
        elif direction == 1:
            if value > values[extreme_index]:
                extreme_index = index
            elif values[extreme_index] - value >= threshold:
                pivots.append(extreme_index)
                direction, extreme_index = -1, index
        else:
            if value < values[extreme_index]:
                extreme_index = index
            elif value - values[extreme_index] >= threshold:
                pivots.append(extreme_index)
                direction, extreme_index = 1, index

    return [index for index in pivots if 0 < index < len(values) - 1]


def detect_swing_shot_frames(
    ball_positions,
    fps,
    min_swing_ratio=DEFAULT_MIN_SWING_RATIO,
    smoothing_seconds=DEFAULT_SWING_SMOOTHING_SECONDS,
):
    """Detect shot frames from interpolated ball positions.

    ``min_swing_ratio`` is a fraction of the clip's vertical range (5th to 95th
    percentile of the smoothed ``y``), so the threshold adapts to resolution and
    camera distance without a pixel constant.
    """
    if min_swing_ratio <= 0:
        raise ValueError("Swing ratio must be positive.")

    window = duration_to_odd_frames(smoothing_seconds, fps)
    smoothed = _centered_moving_average(_ball_center_y(ball_positions), window)

    low, high = np.percentile(smoothed, RANGE_PERCENTILES)
    vertical_range = high - low
    if vertical_range <= 0:
        return []

    return zigzag_pivots(smoothed, min_swing_ratio * vertical_range)
