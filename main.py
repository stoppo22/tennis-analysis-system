import argparse

from pipeline import analyze_video


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze a tennis video and generate an annotated output video."
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
    return parser.parse_args()


def main():
    args = parse_args()

    analyze_video(
        input_video_path=args.input,
        output_video_path=args.output,
    )


if __name__ == "__main__":
    main()