import argparse
import pickle
from pathlib import Path

import cv2

from benchmark.annotate_shots import save_annotations
from utils.shot_detection_utils import (
    DEFAULT_SMOOTHING_SECONDS,
    detect_shot_frames,
    interpolate_ball_positions,
)


def validate_cached_detections(detections, expected_frame_count):
    if not isinstance(detections, list):
        raise ValueError("Ball detection cache must contain a list.")
    if len(detections) != expected_frame_count:
        raise ValueError(
            "Ball detection cache frame count does not match the input video: "
            f"{len(detections)} != {expected_frame_count}."
        )


def read_video_metadata(video_path):
    video = cv2.VideoCapture(str(video_path))
    if not video.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = video.get(cv2.CAP_PROP_FPS)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    video.release()

    if fps <= 0 or frame_count <= 0:
        raise ValueError("The video has invalid FPS or no frames.")
    return fps, frame_count


def detect_ball_positions(video_path, tracker, expected_frame_count):
    video = cv2.VideoCapture(str(video_path))
    if not video.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    detections = []

    try:
        while True:
            readable, frame = video.read()
            if not readable:
                break

            detections.append(tracker.detect_frame(frame))
            completed = len(detections)
            if completed % 50 == 0 or completed == expected_frame_count:
                print(f"Ball detection: {completed}/{expected_frame_count} frames")
    finally:
        video.release()

    if len(detections) != expected_frame_count:
        raise ValueError(
            "Decoded frame count does not match the video metadata: "
            f"{len(detections)} != {expected_frame_count}."
        )
    return detections


def run_baseline(
    video_path,
    model_path,
    output_path,
    persistence_seconds=1.0,
    smoothing_seconds=DEFAULT_SMOOTHING_SECONDS,
):
    from pipeline import _build_detection_cache_path
    from trackers import BallTracker

    video_path = Path(video_path)
    model_path = Path(model_path)

    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not model_path.is_file():
        raise FileNotFoundError(f"Ball model not found: {model_path}")

    fps, frame_count = read_video_metadata(video_path)
    cache_directory = Path("tracker_stubs")
    cache_directory.mkdir(parents=True, exist_ok=True)
    cache_path = _build_detection_cache_path(
        cache_directory=cache_directory,
        detector_name="ball_detections",
        video_path=video_path,
        model_path=model_path,
    )
    if cache_path.exists():
        print(f"Using local ball detection cache: {cache_path}")
        with cache_path.open("rb") as cache_file:
            ball_positions = pickle.load(cache_file)
        validate_cached_detections(ball_positions, frame_count)
    else:
        tracker = BallTracker(model_path=str(model_path))
        ball_positions = detect_ball_positions(video_path, tracker, frame_count)
        with cache_path.open("wb") as cache_file:
            pickle.dump(ball_positions, cache_file)
        print(f"Saved local ball detection cache: {cache_path}")

    interpolated_positions = interpolate_ball_positions(ball_positions)
    shot_frames = detect_shot_frames(
        interpolated_positions,
        fps,
        persistence_seconds=persistence_seconds,
        smoothing_seconds=smoothing_seconds,
    )
    save_annotations(output_path, shot_frames, fps)

    print(f"Detector predicted {len(shot_frames)} shot events.")
    print(f"Predictions saved to: {output_path}")
    return shot_frames


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the existing ball-shot baseline and export event times."
    )
    parser.add_argument("--video", required=True, help="Path to the local clip.")
    parser.add_argument(
        "--model",
        default="models/yolov11best.pt",
        help="Path to the ball detection model.",
    )
    parser.add_argument("--output", required=True, help="Prediction CSV path.")
    parser.add_argument(
        "--persistence-seconds",
        type=float,
        default=1.0,
        help="Required persistent direction-change duration (default: 1.0 s).",
    )
    parser.add_argument(
        "--smoothing-seconds",
        type=float,
        default=DEFAULT_SMOOTHING_SECONDS,
        help="Rolling-mean duration (default: 0.20 s).",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()
    run_baseline(
        args.video,
        args.model,
        args.output,
        persistence_seconds=args.persistence_seconds,
        smoothing_seconds=args.smoothing_seconds,
    )


if __name__ == "__main__":
    main()
