import pandas as pd


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
    minimum_change_frames_per_hit=25,
):
    if fps <= 0:
        raise ValueError("FPS must be greater than zero.")
    if (
        not isinstance(minimum_change_frames_per_hit, int)
        or minimum_change_frames_per_hit <= 0
    ):
        raise ValueError("Minimum change frames per hit must be a positive integer.")

    ball_boxes = [position.get(1, []) for position in ball_positions]
    positions = pd.DataFrame(ball_boxes, columns=["x1", "y1", "x2", "y2"])

    positions["ball_hit"] = 0
    positions["mid_y"] = (positions["y1"] + positions["y2"]) / 2
    positions["mid_y_rolling_mean"] = positions["mid_y"].rolling(
        window=5,
        min_periods=1,
        center=False,
    ).mean()
    positions["delta_y"] = positions["mid_y_rolling_mean"].diff().fillna(0)

    following_window = int(minimum_change_frames_per_hit * 1.2)

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

        if change_count > minimum_change_frames_per_hit - 1:
            positions.at[frame_index, "ball_hit"] = 1

    return positions[positions["ball_hit"] == 1].index.tolist()
