"""Annotate the clips that still need ground truth, one after the other.

First pass: every clip of the chosen split whose ``events`` cell in
``sources.csv`` is blank and that has no annotation file yet.

    python -m benchmark.annotate_pending --split test

Second pass (for inter-annotation agreement): clips of the test split that have a
first annotation but no second one, offered in a fixed random order and written to
``benchmark/annotations_second_pass/`` without showing the first pass.

    python -m benchmark.annotate_pending --split test --second-pass

When you have finished, record the event counts in the manifest. A clip with no
shot at all, or fewer than three contacts, is moved to the ``rejected`` split
("no rally"):

    python -m benchmark.annotate_pending --update-manifest

The window needs OpenCV with a graphical interface (``opencv-python``, not the
``headless`` build). Controls are those of ``benchmark.annotate_shots``: space
play/pause, A/D previous/next frame, H mark a contact, U undo, Q save and next clip.
Mark every racket-ball contact of the point, including a faulted serve.
"""

import argparse
import csv
import random
from pathlib import Path

from benchmark.evaluate_events import load_event_times

BENCHMARK_DIRECTORY = Path(__file__).resolve().parent
SECOND_PASS_SEED = 0
MIN_CONTACTS = 3  # a rally needs the serve, a return and at least one more contact


def read_manifest(sources_path):
    with Path(sources_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader), reader.fieldnames


def select_clips(rows, split, annotations_dir, second_pass_dir, second_pass=False):
    """Clips to annotate now, in the order they should be shown."""
    annotations_dir, second_pass_dir = Path(annotations_dir), Path(second_pass_dir)
    selected = []
    for row in rows:
        if row["split"] != split:
            continue
        clip = row["clip"]
        first = annotations_dir / f"{clip}.csv"
        if second_pass:
            if first.is_file() and not (second_pass_dir / f"{clip}.csv").is_file():
                selected.append(clip)
        elif row.get("events", "").strip() == "" and not first.is_file():
            selected.append(clip)

    if second_pass:
        random.Random(SECOND_PASS_SEED).shuffle(selected)
    return selected


def update_manifest(sources_path, annotations_dir):
    """Fill the ``events`` column from the annotation files.

    Returns ``(updated, rejected)`` clip names. Clips with fewer than
    ``MIN_CONTACTS`` events are moved to the ``rejected`` split: they are not
    rallies (for example a faulted serve or a point cut short).
    """
    rows, fieldnames = read_manifest(sources_path)
    annotations_dir = Path(annotations_dir)
    updated, rejected = [], []

    for row in rows:
        if row.get("events", "").strip() != "":
            continue
        path = annotations_dir / f"{row['clip']}.csv"
        if not path.is_file():
            continue
        count = len(load_event_times(path))
        row["events"] = str(count)
        if count < MIN_CONTACTS:
            row["split"] = "rejected"
            row["notes"] = f"rejected: {count} contacts, not a rally (minimum {MIN_CONTACTS})"
            rejected.append(row["clip"])
        else:
            if row.get("notes", "") == "pending annotation":
                row["notes"] = ""
            updated.append(row["clip"])

    with Path(sources_path).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return updated, rejected


def annotate_in_sequence(clips, videos_dir, output_dir):
    from benchmark.annotate_shots import annotate_video  # needs a GUI-enabled OpenCV

    for position, clip in enumerate(clips, start=1):
        video = Path(videos_dir) / f"{clip}.mp4"
        if not video.is_file():
            print(f"[{position}/{len(clips)}] missing video, skipped: {video}")
            continue

        output = Path(output_dir) / f"{clip}.csv"
        print(f"\n[{position}/{len(clips)}] {clip}")
        annotate_video(video, output)

        if output.is_file() and len(load_event_times(output)) < MIN_CONTACTS:
            print(
                f"  Fewer than {MIN_CONTACTS} contacts: this clip is not a rally "
                "and will be rejected when the manifest is updated."
            )
        if position < len(clips):
            answer = input("Press Enter for the next clip, or type q to stop: ").strip().lower()
            if answer == "q":
                break


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--split", choices=["test", "development"], default="test")
    parser.add_argument("--second-pass", action="store_true")
    parser.add_argument("--update-manifest", action="store_true")
    parser.add_argument("--sources", default=BENCHMARK_DIRECTORY / "sources.csv")
    parser.add_argument("--annotations", default=BENCHMARK_DIRECTORY / "annotations")
    parser.add_argument(
        "--second-pass-dir", default=BENCHMARK_DIRECTORY / "annotations_second_pass"
    )
    parser.add_argument("--videos-dir", default="input_videos/benchmark")
    args = parser.parse_args(argv)

    if args.update_manifest:
        updated, rejected = update_manifest(args.sources, args.annotations)
        print(
            f"Updated {len(updated)} clips; rejected {len(rejected)} "
            f"with fewer than {MIN_CONTACTS} contacts."
        )
        return

    rows, _ = read_manifest(args.sources)
    clips = select_clips(
        rows, args.split, args.annotations, args.second_pass_dir, args.second_pass
    )
    if not clips:
        print("Nothing left to annotate for this selection.")
        return

    output_dir = args.second_pass_dir if args.second_pass else args.annotations
    print(f"{len(clips)} clips to annotate ({'second' if args.second_pass else 'first'} pass).")
    annotate_in_sequence(clips, args.videos_dir, output_dir)


if __name__ == "__main__":
    main()
