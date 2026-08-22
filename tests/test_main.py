import unittest

from main import parse_args


class MainArgumentsTest(unittest.TestCase):
    def test_statistics_output_defaults_to_automatic_path(self):
        args = parse_args([])

        self.assertIsNone(args.statistics_output)

    def test_statistics_output_accepts_explicit_path(self):
        args = parse_args(
            [
                "--input",
                "input.mp4",
                "--output",
                "output.avi",
                "--statistics-output",
                "statistics.csv",
            ]
        )

        self.assertEqual(args.input, "input.mp4")
        self.assertEqual(args.output, "output.avi")
        self.assertEqual(args.statistics_output, "statistics.csv")


if __name__ == "__main__":
    unittest.main()
