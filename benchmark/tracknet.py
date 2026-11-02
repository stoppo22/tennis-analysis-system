"""TrackNet tennis dataset: labels, split by video, YOLO export and ball-level scoring.

See ``EXPERIMENT_ball_detector_training.md`` for the protocol this implements. The
dataset has 10 broadcast videos (``game1`` ... ``game10``) at 1280x720, split into rally
clips (``Clip1`` ...), each with the frames ``0000.jpg`` ... and a ``Label.csv`` with the
columns ``file name, visibility, x-coordinate, y-coordinate, status``. Visibility is 0
(ball not in the image), 1 (easily identified), 2 (hard to identify) or 3 (occluded).

    python -m benchmark.tracknet prepare --source <Dataset dir> --output <dir> --box-side 14
    python -m benchmark.tracknet preview --source <Dataset dir> --output <png> --box-side 14

The dataset is not committed and its terms are not stated in the copies found; it is used
for research and evaluation only.
"""

import argparse
import csv
import math
import shutil
from collections import defaultdict
from pathlib import Path

# Split by video, not by frame: consecutive frames are almost identical.
SPLITS = {
    "train": (1, 2, 4, 5, 7, 10),
    "validation": (3, 8),
    "test": (6, 9),
}
IMAGE_SIZE = (1280, 720)
FRAME_STRIDE = 4
TOLERANCE_FRACTION = 0.0125  # of the frame width: 16 px at 1280
BLOCK_FRAMES = 150  # five seconds at 30 FPS: the unit of the bootstrap

ABSENT, VISIBLE = 0, 1


def split_of_game(game):
    for split, games in SPLITS.items():
        if game in games:
            return split
    raise ValueError(f"Game {game} is not in any split.")


def read_labels(path):
    """Rows of a ``Label.csv`` as dicts with ``frame``, ``number``, ``visibility``, ``x``, ``y``."""
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            name = row["file name"].strip()
            x_text, y_text = row["x-coordinate"].strip(), row["y-coordinate"].strip()
            rows.append(
                {
                    "frame": name,
                    "number": int(Path(name).stem),
                    "visibility": int(row["visibility"]),
                    "x": float(x_text) if x_text else None,
                    "y": float(y_text) if y_text else None,
                }
            )
    return rows


def list_clips(source_root):
    """``[(game, clip_name, directory)]`` in a stable order."""
    clips = []
    for game_dir in Path(source_root).glob("game*"):
        suffix = game_dir.name[4:]
        if not game_dir.is_dir() or not suffix.isdigit():
            continue
        for clip_dir in game_dir.glob("Clip*"):
            clip_suffix = clip_dir.name[4:]
            if clip_dir.is_dir() and clip_suffix.isdigit():
                clips.append((int(suffix), clip_dir.name, clip_dir, int(clip_suffix)))
    clips.sort(key=lambda item: (item[0], item[3]))
    return [(game, name, directory) for game, name, directory, _ in clips]


def select_rows(rows, stride=FRAME_STRIDE):
    """Every ``stride``-th frame, keeping only classes 0 (absent) and 1 (visible).

    Classes 2 and 3 are left out: it is not clear that a ball can be seen in them.
    """
    if stride < 1:
        raise ValueError("Stride must be at least 1.")
    return [
        row
        for position, row in enumerate(rows)
        if position % stride == 0
        and (
            row["visibility"] == ABSENT
            or (row["visibility"] == VISIBLE and row["x"] is not None and row["y"] is not None)
        )
    ]


def yolo_label_line(x, y, box_side, image_size=IMAGE_SIZE):
    """YOLO line (class 0) for a square box of ``box_side`` pixels centred on a point.

    The box is clipped to the image.
    """
    width, height = image_size
    half = box_side / 2.0
    x1, x2 = max(0.0, x - half), min(float(width), x + half)
    y1, y2 = max(0.0, y - half), min(float(height), y + half)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("The point lies outside the image.")
    return (
        f"0 {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} "
        f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}"
    )


def prepare_dataset(source_root, output_root, box_side, stride=FRAME_STRIDE, splits=None):
    """Write a YOLO dataset (images, labels, ``data.yaml``, ``manifest.csv``).

    Returns ``{split: {"positives": n, "negatives": n}}``.
    """
    source_root, output_root = Path(source_root), Path(output_root)
    wanted = set(splits) if splits else set(SPLITS)
    totals = {split: {"positives": 0, "negatives": 0} for split in SPLITS if split in wanted}
    manifest = []

    for game, clip, directory in list_clips(source_root):
        split = split_of_game(game)
        if split not in wanted:
            continue
        label_file = directory / "Label.csv"
        if not label_file.is_file():
            continue
        for row in select_rows(read_labels(label_file), stride):
            image = directory / row["frame"]
            if not image.is_file():
                continue
            stem = f"game{game}_{clip}_{Path(row['frame']).stem}"
            image_out = output_root / "images" / split / f"{stem}.jpg"
            label_out = output_root / "labels" / split / f"{stem}.txt"
            image_out.parent.mkdir(parents=True, exist_ok=True)
            label_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image, image_out)
            if row["visibility"] == VISIBLE:
                label_out.write_text(yolo_label_line(row["x"], row["y"], box_side) + "\n")
                totals[split]["positives"] += 1
            else:
                label_out.write_text("")
                totals[split]["negatives"] += 1
            manifest.append(
                [split, game, clip, row["number"], row["visibility"], row["x"], row["y"]]
            )

    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "manifest.csv").open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(["split", "game", "clip", "frame", "visibility", "x", "y"])
        writer.writerows(manifest)
    (output_root / "data.yaml").write_text(
        f"path: {output_root.resolve()}\n"
        "train: images/train\n"
        "val: images/validation\n"
        "test: images/test\n"
        "names:\n  0: tennis ball\n"
    )
    return totals


def ball_frame_counts(clip, frames, tolerance_pixels):
    """Counts for the bootstrap, ``{(clip, block): (tp, fp, fn)}``, plus a summary.

    ``frames`` yields ``(frame_number, visibility, label_xy, detection_xy)`` where the
    detection is the most confident one of the frame, or ``None``. A visible frame is a
    true positive if the detection is within ``tolerance_pixels`` of the label; otherwise
    it is a miss, and also a false positive if there was a detection elsewhere. A detection
    in a frame without a ball is a false positive.
    """
    counts = defaultdict(lambda: [0, 0, 0])
    summary = {"visible": 0, "found": 0, "absent": 0, "absent_with_detection": 0}
    for number, visibility, label, detection in frames:
        block = counts[(clip, number // BLOCK_FRAMES)]
        if visibility == VISIBLE:
            summary["visible"] += 1
            near = (
                detection is not None
                and math.hypot(detection[0] - label[0], detection[1] - label[1])
                <= tolerance_pixels
            )
            if near:
                block[0] += 1
                summary["found"] += 1
            else:
                block[2] += 1
                if detection is not None:
                    block[1] += 1
        elif visibility == ABSENT:
            summary["absent"] += 1
            if detection is not None:
                block[1] += 1
                summary["absent_with_detection"] += 1
    return {key: tuple(value) for key, value in counts.items()}, summary


def merge_summaries(summaries):
    total = {"visible": 0, "found": 0, "absent": 0, "absent_with_detection": 0}
    for summary in summaries:
        for key in total:
            total[key] += summary[key]
    return total


def _preview(source_root, output_path, box_side, count=50):
    import cv2  # imported here: only needed for this command
    import numpy as np

    rows = []
    for game, clip, directory in list_clips(source_root):
        label_file = directory / "Label.csv"
        if label_file.is_file():
            visible = [r for r in read_labels(label_file) if r["visibility"] == VISIBLE]
            rows += [(directory / r["frame"], r) for r in visible[:: max(1, len(visible) // 3)][:3]]
    step = max(1, len(rows) // count)
    chosen = rows[::step][:count]

    tiles = []
    crop = 48
    for image_path, row in chosen:
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        x, y = int(row["x"]), int(row["y"])
        padded = cv2.copyMakeBorder(image, crop, crop, crop, crop, cv2.BORDER_CONSTANT)
        tile = padded[y : y + 2 * crop, x : x + 2 * crop].copy()
        tile = cv2.resize(tile, (4 * 2 * crop, 4 * 2 * crop), interpolation=cv2.INTER_NEAREST)
        half = int(box_side / 2 * 4)
        centre = 4 * crop
        cv2.rectangle(
            tile, (centre - half, centre - half), (centre + half, centre + half), (0, 255, 0), 1
        )
        tiles.append(tile)
    columns = 5
    while len(tiles) % columns:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i : i + columns]) for i in range(0, len(tiles), columns)])
    cv2.imwrite(str(output_path), grid)
    print(f"{len(chosen)} crops written to {output_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Write the YOLO dataset.")
    prepare.add_argument("--source", required=True)
    prepare.add_argument("--output", required=True)
    prepare.add_argument("--box-side", type=float, required=True, help="Square box side in pixels.")
    prepare.add_argument("--stride", type=int, default=FRAME_STRIDE)
    preview = sub.add_parser("preview", help="Magnified crops with the box, to check its size.")
    preview.add_argument("--source", required=True)
    preview.add_argument("--output", required=True)
    preview.add_argument("--box-side", type=float, required=True)
    args = parser.parse_args(argv)

    if args.command == "prepare":
        totals = prepare_dataset(args.source, args.output, args.box_side, args.stride)
        for split, counts in totals.items():
            print(f"{split}: {counts['positives']} positives, {counts['negatives']} negatives")
    else:
        _preview(args.source, args.output, args.box_side)


if __name__ == "__main__":
    main()
