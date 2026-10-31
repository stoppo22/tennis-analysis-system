"""Ball detections as plain CSV files.

Detection caches are pickles tied to a local video and model. For reproducible
experiments, the raw per-frame ball boxes can be exported once to
``benchmark/detections/<clip>.csv`` (columns ``frame,x1,y1,x2,y2``; empty cells
mean the model did not detect the ball in that frame). The files contain only
box coordinates, not video content, so shot-detection methods can then be
developed and re-run without the videos or model weights.

Export (on the machine that has the video and cache):
    python -m benchmark.detections export --cache tracker_stubs/ball_detections_<hash>.pkl \
        --output benchmark/detections/<clip>.csv
"""

import argparse
import csv
import math
import pickle
from pathlib import Path

FIELDNAMES = ["frame", "x1", "y1", "x2", "y2"]


def _validate_detections(detections):
    if not isinstance(detections, list):
        raise ValueError("Ball detections must be a list with one entry per frame.")
    for frame, entry in enumerate(detections):
        if not isinstance(entry, dict):
            raise ValueError(f"Frame {frame}: detection entry must be a dict.")
        box = entry.get(1)
        if box in (None, [], ()):
            continue
        if len(box) != 4 or not all(math.isfinite(float(v)) for v in box):
            raise ValueError(f"Frame {frame}: expected four finite box values.")


def save_detections_csv(detections, output_path):
    """Write per-frame ball boxes; frames without a detection stay empty."""
    _validate_detections(detections)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(FIELDNAMES)
        for frame, entry in enumerate(detections):
            box = entry.get(1)
            if box in (None, [], ()):
                writer.writerow([frame, "", "", "", ""])
            else:
                writer.writerow([frame] + [f"{float(v):.4f}" for v in box])
    return output_path


def load_detections_csv(csv_path):
    """Read a detections CSV back into the pipeline's ``[{1: box} | {}]`` form."""
    detections = []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != FIELDNAMES:
            raise ValueError(f"{csv_path} must have columns {FIELDNAMES}.")
        for expected_frame, row in enumerate(reader):
            if int(row["frame"]) != expected_frame:
                raise ValueError(
                    f"{csv_path}: frames must be consecutive from 0 "
                    f"(expected {expected_frame}, found {row['frame']})."
                )
            values = [row[name] for name in FIELDNAMES[1:]]
            if all(value == "" for value in values):
                detections.append({})
            elif any(value == "" for value in values):
                raise ValueError(f"{csv_path}: partial box at frame {expected_frame}.")
            else:
                detections.append({1: [float(value) for value in values]})
    if not detections:
        raise ValueError(f"{csv_path} contains no frames.")
    return detections


def export_cache(cache_path, output_path):
    with open(cache_path, "rb") as cache_file:
        detections = pickle.load(cache_file)
    save_detections_csv(detections, output_path)
    detected = sum(1 for entry in detections if entry.get(1))
    print(
        f"Exported {len(detections)} frames ({detected} with a detection, "
        f"{detected / len(detections):.1%}) to {output_path}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ball detection CSV utilities.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    export = subcommands.add_parser("export", help="Convert a local pickle cache to CSV.")
    export.add_argument("--cache", required=True, help="Local ball detection .pkl cache.")
    export.add_argument("--output", required=True, help="Destination CSV path.")
    args = parser.parse_args(argv)

    if args.command == "export":
        export_cache(args.cache, args.output)


if __name__ == "__main__":
    main()
