import unittest

import numpy as np

from tennis_analysis.utils.shot_detectors import (
    SHOT_DETECTORS,
    detect_shots,
    validate_shot_detector,
)


def zigzag_positions(turning_values, samples_between):
    values = []
    for start, end in zip(turning_values, turning_values[1:]):
        values.extend(np.linspace(start, end, samples_between, endpoint=False))
    values.append(turning_values[-1])
    return [{1: [100.0, y - 3, 106.0, y + 3]} for y in values]


class ShotDetectorsTest(unittest.TestCase):
    def test_available_detectors(self):
        self.assertEqual(set(SHOT_DETECTORS), {"persistence", "swing"})

    def test_unknown_detector_lists_the_available_names(self):
        with self.assertRaises(ValueError) as context:
            validate_shot_detector("magic")

        message = str(context.exception)
        self.assertIn("magic", message)
        self.assertIn("persistence", message)
        self.assertIn("swing", message)

    def test_both_detectors_find_clear_swings(self):
        positions = zigzag_positions([600, 200, 600, 200, 600, 200, 600], 30)

        for name in SHOT_DETECTORS:
            with self.subTest(name):
                frames = detect_shots(name, positions, fps=25.0)
                self.assertGreaterEqual(len(frames), 3)
                self.assertEqual(frames, sorted(frames))


if __name__ == "__main__":
    unittest.main()
