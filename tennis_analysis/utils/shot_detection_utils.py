import math

import pandas as pd


DEFAULT_SHOT_PERSISTENCE_SECONDS = 0.72
DEFAULT_SMOOTHING_SECONDS = 0.20
FOLLOWING_WINDOW_RATIO = 1.2


def duration_to_frames(duration_seconds, fps):
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("FPS must be a finite number greater than zero.")
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("Duration must be a finite number greater than zero.")

    return max(1, math.floor(duration_seconds * fps + 0.5))


def duration_to_odd_frames(duration_seconds, fps):
    frame_count = duration_to_frames(duration_seconds, fps)
    if frame_count % 2 == 0:
        frame_count += 1
    return frame_count


def interpolate_ball_positions(ball_positions):
    ball_boxes = [position.get(1, []) for position in ball_positions]
    if not any(ball_boxes):
        raise ValueError(
            "Cannot interpolate ball positions because no ball was detected"
        )

    positions = pd.DataFrame(ball_boxes, columns=["x1", "y1", "x2", "y2"])
    if positions.dropna(how="all").empty:
        raise ValueError(
            "Cannot interpolate ball positions because no ball was detected"
        )

    positions = positions.interpolate().bfill()
    return [{1: box} for box in positions.to_numpy().tolist()]


def detect_shot_frames(
    ball_positions,
    fps,
    persistence_seconds=DEFAULT_SHOT_PERSISTENCE_SECONDS,
    smoothing_seconds=DEFAULT_SMOOTHING_SECONDS,
):
    persistence_frames = duration_to_frames(persistence_seconds, fps)
    smoothing_frames = duration_to_odd_frames(smoothing_seconds, fps)

    ball_boxes = [position.get(1, []) for position in ball_positions]
    positions = pd.DataFrame(ball_boxes, columns=["x1", "y1", "x2", "y2"])

    positions["ball_hit"] = 0
    positions["mid_y"] = (positions["y1"] + positions["y2"]) / 2
    positions["mid_y_rolling_mean"] = positions["mid_y"].rolling(
        window=smoothing_frames,
        min_periods=1,
        center=False,
    ).mean()
    positions["delta_y"] = positions["mid_y_rolling_mean"].diff().fillna(0)

    following_window = int(persistence_frames * FOLLOWING_WINDOW_RATIO)

    for frame_index in range(1, len(positions) - following_window):
        changes_from_positive_to_negative = (
            positions["delta_y"].iloc[frame_index] > 0
            and positions["delta_y"].iloc[frame_index + 1] < 0
        )
        changes_from_negative_to_positive = (
            positions["delta_y"].iloc[frame_index] < 0
            and positions["delta_y"].iloc[frame_index + 1] > 0
        )

        if not (
            changes_from_positive_to_negative
            or changes_from_negative_to_positive
        ):
            continue

        change_count = 0
        for following_frame in range(
            frame_index + 1,
            frame_index + following_window + 1,
        ):
            keeps_negative_direction = (
                positions["delta_y"].iloc[frame_index] > 0
                and positions["delta_y"].iloc[following_frame] < 0
            )
            keeps_positive_direction = (
                positions["delta_y"].iloc[frame_index] < 0
                and positions["delta_y"].iloc[following_frame] > 0
            )

            if keeps_negative_direction or keeps_positive_direction:
                change_count += 1

        if change_count > persistence_frames - 1:
            positions.at[frame_index, "ball_hit"] = 1

    return positions[positions["ball_hit"] == 1].index.tolist()
