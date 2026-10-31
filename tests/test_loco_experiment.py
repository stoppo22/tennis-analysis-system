import unittest

from benchmark.loco_experiment import METHODS, selection_key


class SelectionKeyTest(unittest.TestCase):
    def test_higher_f1_wins(self):
        self.assertGreater(selection_key((0.1,), 0.8), selection_key((0.9,), 0.7))

    def test_ties_prefer_larger_parameters(self):
        self.assertGreater(
            selection_key((0.4, 0.36), 0.8), selection_key((0.3, 0.36), 0.8)
        )
        self.assertGreater(
            selection_key((0.4, 0.36), 0.8), selection_key((0.4, 0.28), 0.8)
        )

    def test_float_noise_does_not_break_ties(self):
        self.assertEqual(
            selection_key((0.4,), 0.8), selection_key((0.4,), 0.8 + 1e-15)
        )


class PreRegisteredGridTest(unittest.TestCase):
    def test_grid_sizes_match_the_protocol(self):
        self.assertEqual(len(METHODS["persistence"]["grid"]), 7)
        self.assertEqual(len(METHODS["swing"]["grid"]), 32)


if __name__ == "__main__":
    unittest.main()
