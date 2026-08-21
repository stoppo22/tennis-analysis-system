import math
import unittest

from utils.player_stats_drawer_utils import _format_speed
from utils.player_stats_utils import build_player_stats_dataframe


def initial_stats():
    return {
        "frame_num": 0,
        "player_1_number_of_shots": 0,
        "player_1_total_shot_speed": 0,
        "player_1_last_shot_speed": 0,
        "player_1_total_player_speed": 0,
        "player_1_last_player_speed": 0,
        "player_2_number_of_shots": 0,
        "player_2_total_shot_speed": 0,
        "player_2_last_shot_speed": 0,
        "player_2_total_player_speed": 0,
        "player_2_last_player_speed": 0,
    }


class PlayerStatsTest(unittest.TestCase):
    def test_averages_are_unavailable_without_samples(self):
        stats = build_player_stats_dataframe([initial_stats()], frame_count=3)

        average_columns = [
            "player_1_average_shot_speed",
            "player_2_average_shot_speed",
            "player_1_average_player_speed",
            "player_2_average_player_speed",
        ]
        for column in average_columns:
            self.assertTrue(stats[column].isna().all())

        self.assertEqual(_format_speed(math.nan), "N/A")

    def test_player_speed_uses_opponent_shot_count(self):
        after_player_1_shot = {
            **initial_stats(),
            "frame_num": 10,
            "player_1_number_of_shots": 1,
            "player_1_total_shot_speed": 100,
            "player_2_total_player_speed": 12,
        }
        after_two_player_2_shots = {
            **after_player_1_shot,
            "frame_num": 30,
            "player_2_number_of_shots": 2,
            "player_2_total_shot_speed": 180,
            "player_1_total_player_speed": 20,
        }

        stats = build_player_stats_dataframe(
            [initial_stats(), after_player_1_shot, after_two_player_2_shots],
            frame_count=31,
        )
        final_frame = stats.iloc[-1]

        self.assertEqual(final_frame["player_1_average_player_speed"], 10)
        self.assertEqual(final_frame["player_2_average_player_speed"], 12)
        self.assertEqual(_format_speed(12.34), "12.3 km/h")


if __name__ == "__main__":
    unittest.main()
