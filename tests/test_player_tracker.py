import unittest

from tennis_analysis.trackers.player_tracker import PlayerTracker


class PlayerTrackerTest(unittest.TestCase):
    def test_selected_tracker_ids_are_remapped_to_stable_roles(self):
        bottom_player = [40, 60, 80, 110]
        top_player = [40, 10, 80, 40]
        detections = [
            {7: bottom_player, 3: top_player, 99: [0, 0, 10, 10]},
            {7: [42, 60, 82, 110], 99: [0, 0, 10, 10]},
            {7: [44, 60, 84, 110], 3: [42, 10, 82, 40]},
        ]

        tracker = PlayerTracker.__new__(PlayerTracker)
        tracker.choose_players = lambda court_keypoints, player_dict: [3, 7]

        filtered = tracker.choose_and_filter_players([], detections)

        self.assertEqual(filtered[0], {1: bottom_player, 2: top_player})
        self.assertEqual(filtered[1][2], top_player)
        self.assertEqual(set(filtered[2]), {1, 2})


if __name__ == "__main__":
    unittest.main()
