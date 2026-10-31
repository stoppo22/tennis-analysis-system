import argparse

from tennis_analysis.pipeline import (
    DEFAULT_BALL_MODEL_PATH,
    DEFAULT_CACHE_DIRECTORY,
    DEFAULT_COURT_MODEL_PATH,
    DEFAULT_PLAYER_MODEL_PATH,
    analyze_video,
)
from tennis_analysis.utils.shot_detectors import DEFAULT_SHOT_DETECTOR, SHOT_DETECTORS


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="tennis-analysis",
        description=(
            "Analyze a tennis video and generate an annotated video plus a "
            "per-frame statistics CSV."
        ),
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
    parser.add_argument(
        "--shot-detector",
        choices=sorted(SHOT_DETECTORS),
        default=DEFAULT_SHOT_DETECTOR,
        help=(
            "Shot-event method (default: %(default)s). 'swing' is the "
            "alternating-swing detector, supported so far by development "
            "evidence only; see benchmark/EXPERIMENT_swing_detector.md."
        ),
    )
    parser.add_argument(
        "--player-model",
        default=DEFAULT_PLAYER_MODEL_PATH,
        help="Player detection weights (default: %(default)s).",
    )
    parser.add_argument(
        "--ball-model",
        default=DEFAULT_BALL_MODEL_PATH,
        help="Ball detection weights (default: %(default)s).",
    )
    parser.add_argument(
        "--court-model",
        default=DEFAULT_COURT_MODEL_PATH,
        help="Court keypoint weights (default: %(default)s).",
    )
    parser.add_argument(
        "--cache-dir",
        default=DEFAULT_CACHE_DIRECTORY,
        help="Directory for detection caches (default: %(default)s).",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    result = analyze_video(
        input_video_path=args.input,
        output_video_path=args.output,
        statistics_output_path=args.statistics_output,
        player_model_path=args.player_model,
        ball_model_path=args.ball_model,
        court_model_path=args.court_model,
        cache_directory=args.cache_dir,
        shot_detector=args.shot_detector,
    )

    print(f"Annotated video: {result['output_video_path']}")
    print(f"Statistics CSV: {result['statistics_csv_path']}")
    print(
        f"Shots detected ({result['shot_detector']}): "
        f"{len(result['detected_shot_frames'])}"
    )


if __name__ == "__main__":
    main()
