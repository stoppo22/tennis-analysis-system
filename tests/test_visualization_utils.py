import unittest

import numpy as np

from mini_court import MiniCourt
from utils.player_stats_drawer_utils import _get_stats_panel_bounds
from utils.visualization_utils import (
    draw_corner_box,
    draw_label,
    draw_translucent_panel,
)


class VisualizationUtilsTest(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((120, 160, 3), dtype=np.uint8)

    def test_translucent_panel_changes_only_its_area(self):
        draw_translucent_panel(
            self.frame,
            (20, 20),
            (140, 100),
            color=(100, 120, 140),
            opacity=0.5,
        )

        self.assertTrue(np.any(self.frame[60, 80] > 0))
        self.assertTrue(np.all(self.frame[5, 5] == 0))

    def test_corner_box_leaves_middle_of_edges_clear(self):
        draw_corner_box(
            self.frame,
            (20, 20, 140, 100),
            color=(10, 200, 250),
            corner_length=15,
            thickness=2,
        )

        self.assertTrue(np.any(self.frame[20, 20] > 0))
        self.assertTrue(np.all(self.frame[20, 80] == 0))

    def test_label_draws_above_detection(self):
        draw_label(
            self.frame,
            "P1",
            (30, 50),
            color=(70, 190, 255),
        )

        self.assertTrue(np.any(self.frame[:55, 25:80] > 0))

    def test_720p_dashboard_panels_do_not_overlap(self):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        mini_court = MiniCourt(frame)
        start_x, start_y, end_x, end_y, _ = _get_stats_panel_bounds(frame)

        self.assertGreater(start_y, mini_court.end_y)
        self.assertEqual(end_x, mini_court.end_x)
        self.assertLessEqual(end_y, frame.shape[0])
        self.assertGreaterEqual(start_x, 0)


if __name__ == "__main__":
    unittest.main()
