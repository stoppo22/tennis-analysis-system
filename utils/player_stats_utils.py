from pathlib import Path

import pandas as pd

import constants
from .bbox_utils import measure_distance
from .conversions import convert_pixel_distance_to_meters


SAMPLE_COUNT_COLUMNS = (
    "player_1_shot_speed_samples",
    "player_2_shot_speed_samples",
    "player_1_player_speed_samples",
    "player_2_player_speed_samples",
)


def _initial_player_stats():
    stats = {"frame_num": 0}
    for player_id in (1, 2):
        stats.update(
            {
                f"player_{player_id}_number_of_shots": 0,
                f"player_{player_id}_total_shot_speed": 0,
                f"player_{player_id}_last_shot_speed": 0,
                f"player_{player_id}_total_player_speed": 0,
                f"player_{player_id}_last_player_speed": 0,
                f"player_{player_id}_shot_speed_samples": 0,
                f"player_{player_id}_player_speed_samples": 0,
            }
        )
    return stats


def calculate_player_stats_data(
    ball_shot_frames,
    player_positions,
    ball_positions,
    fps,
    mini_court_width,
):
    """Build correctly timed shot counts and speed samples."""
    if fps <= 0:
        raise ValueError(f"FPS must be positive, received {fps}")
    if mini_court_width <= 0:
        raise ValueError("Mini-court width must be positive")

    stats_data = [_initial_player_stats()]
    previous_frame = None
    previous_hitter = None

    for shot_frame in ball_shot_frames:
        current_stats = dict(stats_data[-1])
        current_stats["frame_num"] = shot_frame

        frame_player_positions = player_positions[shot_frame]
        ball_position = ball_positions[shot_frame][1]
        hitter = min(
            frame_player_positions,
            key=lambda player_id: measure_distance(
                frame_player_positions[player_id],
                ball_position,
            ),
        )

        if previous_frame is not None:
            elapsed_seconds = (shot_frame - previous_frame) / fps
            if elapsed_seconds <= 0:
                raise ValueError("Shot frames must be strictly increasing")

            ball_distance_pixels = measure_distance(
                ball_positions[previous_frame][1],
                ball_position,
            )
            ball_distance_meters = convert_pixel_distance_to_meters(
                ball_distance_pixels,
                constants.DOUBLE_LINE_WIDTH,
                mini_court_width,
            )
            shot_speed = ball_distance_meters / elapsed_seconds * 3.6
            current_stats[
                f"player_{previous_hitter}_total_shot_speed"
            ] += shot_speed
            current_stats[
                f"player_{previous_hitter}_last_shot_speed"
            ] = shot_speed
            current_stats[
                f"player_{previous_hitter}_shot_speed_samples"
            ] += 1

            returning_player = 1 if previous_hitter == 2 else 2
            player_distance_pixels = measure_distance(
                player_positions[previous_frame][returning_player],
                frame_player_positions[returning_player],
            )
            player_distance_meters = convert_pixel_distance_to_meters(
                player_distance_pixels,
                constants.DOUBLE_LINE_WIDTH,
                mini_court_width,
            )
            player_speed = player_distance_meters / elapsed_seconds * 3.6
            current_stats[
                f"player_{returning_player}_total_player_speed"
            ] += player_speed
            current_stats[
                f"player_{returning_player}_last_player_speed"
            ] = player_speed
            current_stats[
                f"player_{returning_player}_player_speed_samples"
            ] += 1

        current_stats[f"player_{hitter}_number_of_shots"] += 1

        if shot_frame == stats_data[-1]["frame_num"]:
            stats_data[-1] = current_stats
        else:
            stats_data.append(current_stats)

        previous_frame = shot_frame
        previous_hitter = hitter

    return stats_data


def _average_with_available_samples(total_values, sample_counts):
    """Return averages only where at least one sample is available."""
    averages = total_values / sample_counts
    return averages.where(sample_counts > 0)


def resolve_statistics_output_path(
    output_video_path,
    statistics_output_path=None,
):
    """Return the requested CSV path or derive one from the video path."""
    video_path = Path(output_video_path)
    if statistics_output_path is None:
        statistics_path = video_path.with_name(
            f"{video_path.stem}_statistics.csv"
        )
    else:
        statistics_path = Path(statistics_output_path)

    if statistics_path.resolve() == video_path.resolve():
        raise ValueError(
            "Statistics output path and video output path must be different"
        )

    return statistics_path


def save_player_stats_csv(player_stats, output_path):
    """Save per-frame player statistics without a DataFrame index column."""
    statistics_path = Path(output_path)
    statistics_path.parent.mkdir(parents=True, exist_ok=True)
    player_stats.to_csv(statistics_path, index=False)
    return statistics_path


def build_player_stats_dataframe(player_stats_data, frame_count):
    """Expand event statistics to every video frame and calculate averages."""
    player_stats_data_df = pd.DataFrame(player_stats_data)
    frames_df = pd.DataFrame({"frame_num": range(frame_count)})
    player_stats_data_df = pd.merge(
        frames_df,
        player_stats_data_df,
        on="frame_num",
        how="left",
    ).ffill()

    player_1_shot_samples = player_stats_data_df.get(
        "player_1_shot_speed_samples",
        player_stats_data_df["player_1_number_of_shots"],
    )
    player_2_shot_samples = player_stats_data_df.get(
        "player_2_shot_speed_samples",
        player_stats_data_df["player_2_number_of_shots"],
    )
    player_1_movement_samples = player_stats_data_df.get(
        "player_1_player_speed_samples",
        player_stats_data_df["player_2_number_of_shots"],
    )
    player_2_movement_samples = player_stats_data_df.get(
        "player_2_player_speed_samples",
        player_stats_data_df["player_1_number_of_shots"],
    )

    player_stats_data_df["player_1_average_shot_speed"] = (
        _average_with_available_samples(
            player_stats_data_df["player_1_total_shot_speed"],
            player_1_shot_samples,
        )
    )
    player_stats_data_df["player_2_average_shot_speed"] = (
        _average_with_available_samples(
            player_stats_data_df["player_2_total_shot_speed"],
            player_2_shot_samples,
        )
    )

    # A player's movement speed is sampled while returning the opponent's shot.
    # Therefore player 1 has one movement sample per player 2 shot, and vice versa.
    player_stats_data_df["player_1_average_player_speed"] = (
        _average_with_available_samples(
            player_stats_data_df["player_1_total_player_speed"],
            player_1_movement_samples,
        )
    )
    player_stats_data_df["player_2_average_player_speed"] = (
        _average_with_available_samples(
            player_stats_data_df["player_2_total_player_speed"],
            player_2_movement_samples,
        )
    )

    return player_stats_data_df.drop(
        columns=list(SAMPLE_COUNT_COLUMNS),
        errors="ignore",
    )
