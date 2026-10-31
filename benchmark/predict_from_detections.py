"""Write shot-event predictions for every clip from stored ball detections.

For each clip of the chosen splits that has a detections CSV, the ball positions are
interpolated and every requested method is run with the clip's frame rate, writing
``<predictions>/<clip>_<method>.csv`` in the format read by
``benchmark.run_benchmark``.

    python -m benchmark.predict_from_detections --splits test \
        --detections runs/yolo11l/detections

Methods are fixed here so that a run is reproducible:

- ``baseline``: persistence rule, 1.0 s (the original behaviour at 25 FPS);
- ``persistence_18``: persistence rule, 0.72 s (the v0.5 development selection);
- ``swing_v1``: alternating-swing detector with its frozen default parameters.
"""

import argparse
import csv
from pathlib import Path

from benchmark.annotate_shots import save_annotations
from benchmark.detections import load_detections_csv
from tennis_analysis.utils.shot_detection_utils import (
    DEFAULT_SMOOTHING_SECONDS,
    detect_shot_frames,
    interpolate_ball_positions,
)
from tennis_analysis.utils.swing_shot_detection import detect_swing_shot_frames

BENCHMARK_DIRECTORY = Path(__file__).resolve().parent

METHODS = {
    "baseline": lambda positions, fps: detect_shot_frames(
        positions, fps, persistence_seconds=1.0, smoothing_seconds=DEFAULT_SMOOTHING_SECONDS
    ),
    "persistence_18": lambda positions, fps: detect_shot_frames(
        positions, fps, persistence_seconds=0.72, smoothing_seconds=DEFAULT_SMOOTHING_SECONDS
    ),
    "swing_v1": lambda positions, fps: detect_swing_shot_frames(positions, fps),
}


def predict_clip(detections, fps, method):
    """Shot frames for one clip; a clip without any detected ball has no events."""
    try:
        positions = interpolate_ball_positions(detections)
    except ValueError:
        return []
    return [int(frame) for frame in METHODS[method](positions, fps)]


def clips_with_fps(sources_path, splits):
    with Path(sources_path).open(newline="", encoding="utf-8") as csv_file:
        return {
            row["clip"]: float(row["fps"])
            for row in csv.DictReader(csv_file)
            if row["split"] in splits and row["fps"].strip()
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--splits", nargs="+", default=["test"])
    parser.add_argument("--methods", nargs="+", choices=sorted(METHODS), default=sorted(METHODS))
    parser.add_argument("--detections", required=True, help="Directory of <clip>.csv detections.")
    parser.add_argument("--sources", default=BENCHMARK_DIRECTORY / "sources.csv")
    parser.add_argument("--output-dir", default=BENCHMARK_DIRECTORY / "predictions")
    args = parser.parse_args(argv)

    clips = clips_with_fps(args.sources, set(args.splits))
    written = 0
    for clip, fps in sorted(clips.items()):
        path = Path(args.detections) / f"{clip}.csv"
        if not path.is_file():
            print(f"missing detections, skipped: {clip}")
            continue
        detections = load_detections_csv(path)
        for method in args.methods:
            frames = predict_clip(detections, fps, method)
            save_annotations(Path(args.output_dir) / f"{clip}_{method}.csv", frames, fps)
            written += 1
        print(f"{clip}: " + ", ".join(
            f"{m} {len(predict_clip(detections, fps, m))}" for m in args.methods))
    print(f"\n{written} prediction files written to {args.output_dir}")


if __name__ == "__main__":
    main()
