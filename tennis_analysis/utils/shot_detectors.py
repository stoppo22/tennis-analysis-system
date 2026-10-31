"""Registry of the available shot-event detectors.

Both detectors take interpolated ball positions and the video frame rate and
return the frame indices of detected shots.
"""

from tennis_analysis.utils.shot_detection_utils import (
    DEFAULT_SHOT_PERSISTENCE_SECONDS,
    DEFAULT_SMOOTHING_SECONDS,
    detect_shot_frames,
)
from tennis_analysis.utils.swing_shot_detection import detect_swing_shot_frames

DEFAULT_SHOT_DETECTOR = "persistence"


def _persistence(ball_positions, fps):
    return detect_shot_frames(
        ball_positions,
        fps,
        persistence_seconds=DEFAULT_SHOT_PERSISTENCE_SECONDS,
        smoothing_seconds=DEFAULT_SMOOTHING_SECONDS,
    )


def _swing(ball_positions, fps):
    return detect_swing_shot_frames(ball_positions, fps)


SHOT_DETECTORS = {
    "persistence": _persistence,
    "swing": _swing,
}


def validate_shot_detector(detector_name):
    """Raise ``ValueError`` listing the available names if ``detector_name`` is unknown."""
    if detector_name not in SHOT_DETECTORS:
        available = ", ".join(sorted(SHOT_DETECTORS))
        raise ValueError(
            f"Unknown shot detector '{detector_name}'. Available: {available}."
        )


def detect_shots(detector_name, ball_positions, fps):
    """Run the named detector on interpolated ball positions."""
    validate_shot_detector(detector_name)
    return SHOT_DETECTORS[detector_name](ball_positions, fps)
