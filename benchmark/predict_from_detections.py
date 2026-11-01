"""Write shot-event predictions for every clip from stored ball detections.

For each clip of the chosen splits that has a detections CSV, the ball positions are
interpolated and every requested method is run with the clip's frame rate, writing
``<predictions>/<clip>_<method>.csv`` in the format read by
``benchmark.run_benchmark``.

    python -m benchmark.predict_from_detections --splits test \
        --detections runs/yolo11l/detections

With ``--suppress-static`` the detections that stay in the same place for about a
second (marks on the court mistaken for the ball) are removed first, and the files
are named ``<clip>_<method>_nostatic.csv``.

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
from tennis_analysis.utils.detection_filters import suppress_static_detections
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


def clip_widths(sources_path, splits):
    """Frame width in pixels of each clip, from the ``resolution`` column."""
    with Path(sources_path).open(newline="", encoding="utf-8") as csv_file:
        return {
            row["clip"]: int(row["resolution"].split("x")[0])
            for row in csv.DictReader(csv_file)
            if row["split"] in splits and row.get("resolution", "").strip()
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--splits", nargs="+", default=["test"])
    parser.add_argument("--methods", nargs="+", choices=sorted(METHODS), default=sorted(METHODS))
    parser.add_argument("--detections", required=True, help="Directory of <clip>.csv detections.")
    parser.add_argument("--sources", default=BENCHMARK_DIRECTORY / "sources.csv")
    parser.add_argument("--output-dir", default=BENCHMARK_DIRECTORY / "predictions")
    parser.add_argument(
        "--tag",
        default="",
        help="Extra label appended to the method name in the output file names.",
    )
    parser.add_argument(
        "--suppress-static",
        action="store_true",
        help="Remove detections that stay in the same place for about a second first.",
    )
    args = parser.parse_args(argv)

    clips = clips_with_fps(args.sources, set(args.splits))
    widths = clip_widths(args.sources, set(args.splits))
    suffix = ("_nostatic" if args.suppress_static else "") + (f"_{args.tag}" if args.tag else "")
    written = 0
    for clip, fps in sorted(clips.items()):
        path = Path(args.detections) / f"{clip}.csv"
        if not path.is_file():
            print(f"missing detections, skipped: {clip}")
            continue
        detections = load_detections_csv(path)
        removed = 0
        if args.suppress_static:
            detections, removed = suppress_static_detections(detections, fps, widths[clip])
        counts = {}
        for method in args.methods:
            frames = predict_clip(detections, fps, method)
            save_annotations(Path(args.output_dir) / f"{clip}_{method}{suffix}.csv", frames, fps)
            counts[method] = len(frames)
            written += 1
        extra = f" (static detections removed: {removed})" if args.suppress_static else ""
        print(f"{clip}: " + ", ".join(f"{m} {n}" for m, n in counts.items()) + extra)
    print(f"\n{written} prediction files written to {args.output_dir}")


if __name__ == "__main__":
    main()
