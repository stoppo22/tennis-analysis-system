import pandas as pd


def _average_with_available_samples(total_values, sample_counts):
    """Return averages only where at least one sample is available."""
    averages = total_values / sample_counts
    return averages.where(sample_counts > 0)


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

    player_stats_data_df["player_1_average_shot_speed"] = (
        _average_with_available_samples(
            player_stats_data_df["player_1_total_shot_speed"],
            player_stats_data_df["player_1_number_of_shots"],
        )
    )
    player_stats_data_df["player_2_average_shot_speed"] = (
        _average_with_available_samples(
            player_stats_data_df["player_2_total_shot_speed"],
            player_stats_data_df["player_2_number_of_shots"],
        )
    )

    # A player's movement speed is sampled while returning the opponent's shot.
    # Therefore player 1 has one movement sample per player 2 shot, and vice versa.
    player_stats_data_df["player_1_average_player_speed"] = (
        _average_with_available_samples(
            player_stats_data_df["player_1_total_player_speed"],
            player_stats_data_df["player_2_number_of_shots"],
        )
    )
    player_stats_data_df["player_2_average_player_speed"] = (
        _average_with_available_samples(
            player_stats_data_df["player_2_total_player_speed"],
            player_stats_data_df["player_1_number_of_shots"],
        )
    )

    return player_stats_data_df
