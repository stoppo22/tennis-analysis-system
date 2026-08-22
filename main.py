import argparse

from pipeline import analyze_video


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Analyze a tennis video and generate an annotated video plus a "
            "per-frame statistics CSV."
        )
    )
    parser.add_argument(
        "--input",
        default="input_videos/input_video.mp4",
        help="Path to the input tennis video.",
    )
    parser.add_argument(
        "--output",
        default="output_videos/output_video.avi",
        help="Path where the annotated video will be saved.",
    )
    parser.add_argument(
        "--statistics-output",
        default=None,
        help=(
            "Optional CSV output path. By default, it is saved next to the "
            "annotated video with a _statistics.csv suffix."
        ),
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()

    result = analyze_video(
        input_video_path=args.input,
        output_video_path=args.output,
        statistics_output_path=args.statistics_output,
    )

    print(f"Annotated video: {result['output_video_path']}")
    print(f"Statistics CSV: {result['statistics_csv_path']}")


if __name__ == "__main__":
    main()
