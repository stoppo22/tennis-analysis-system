"""Check a candidate benchmark clip against the selection protocol.

The requirements in ``CLIP_SELECTION.md`` are verified automatically where
possible: a single continuous shot (no cuts, replays or slow motion
transitions), a steady camera, resolution, frame rate and duration. The script
also computes the SHA-256 of the file and prints a ``sources.csv`` row.

    python -m benchmark.check_clip input_videos/benchmark/<clip>.mp4

A passing report does not replace a visual check: the court must be fully
visible, both players on court, singles only, and no replay or slow motion.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

ANALYSIS_SIZE = (320, 180)
HISTOGRAM_BINS = 32
CUT_CORRELATION_THRESHOLD = 0.60
CUT_MEAN_DIFFERENCE_THRESHOLD = 25.0
TILE_SIZE = (80, 60)  # 4 x 3 tiles over the analysis frame
MIN_TILE_RESPONSE = 0.05
MIN_RELIABLE_TILES = 4
MAX_CAMERA_DRIFT_FRACTION = 0.03  # of frame width, relative to the first frame

MIN_DURATION_SECONDS = 20.0
MAX_DURATION_SECONDS = 60.0
MIN_WIDTH = 1280
MIN_HEIGHT = 720


def file_sha256(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def to_analysis_frame(frame):
    """Small grayscale float frame used for all comparisons."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    return cv2.resize(gray, ANALYSIS_SIZE, interpolation=cv2.INTER_AREA).astype(
        np.float32
    )


def _histogram(gray_frame):
    histogram = cv2.calcHist(
        [gray_frame.astype(np.uint8)], [0], None, [HISTOGRAM_BINS], [0, 256]
    )
    return cv2.normalize(histogram, histogram).flatten()


def find_cuts(analysis_frames, fps):
    """Return times (s) where consecutive frames differ like a shot change."""
    cuts = []
    previous = None
    previous_histogram = None
    for index, frame in enumerate(analysis_frames):
        histogram = _histogram(frame)
        if previous is not None:
            correlation = cv2.compareHist(
                previous_histogram, histogram, cv2.HISTCMP_CORREL
            )
            mean_difference = float(np.mean(np.abs(frame - previous)))
            if (
                correlation < CUT_CORRELATION_THRESHOLD
                or mean_difference > CUT_MEAN_DIFFERENCE_THRESHOLD
            ):
                cuts.append(round(index / fps, 3))
        previous = frame
        previous_histogram = histogram
    return cuts


def _tile_shifts(reference, frame, tile_window):
    """Phase-correlation shifts per tile as ``[(dx, dy, response)]``."""
    tile_width, tile_height = TILE_SIZE
    shifts = []
    for top in range(0, ANALYSIS_SIZE[1] - tile_height + 1, tile_height):
        for left in range(0, ANALYSIS_SIZE[0] - tile_width + 1, tile_width):
            region = (slice(top, top + tile_height), slice(left, left + tile_width))
            (dx, dy), response = cv2.phaseCorrelate(
                reference[region], frame[region], tile_window
            )
            shifts.append((dx, dy, response))
    return shifts


def measure_camera_drift(analysis_frames, original_width):
    """Largest global shift (in original pixels) relative to the first frame.

    The frame is split into tiles and the *median* tile shift is used, so players
    and the ball moving in a few tiles do not register as camera motion.
    """
    tile_window = cv2.createHanningWindow(TILE_SIZE, cv2.CV_32F)
    reference = analysis_frames[0]
    scale = original_width / ANALYSIS_SIZE[0]

    largest = 0.0
    for frame in analysis_frames[1:]:
        shifts = _tile_shifts(reference, frame, tile_window)
        reliable = [s for s in shifts if s[2] >= MIN_TILE_RESPONSE]
        chosen = reliable if len(reliable) >= MIN_RELIABLE_TILES else shifts
        dx = float(np.median([s[0] for s in chosen]))
        dy = float(np.median([s[1] for s in chosen]))
        largest = max(largest, float(np.hypot(dx, dy)) * scale)
    return largest


def evaluate_requirements(metadata, cuts, camera_drift):
    """Return ``[(requirement, passed, detail)]`` for the protocol checks."""
    width, height = metadata["width"], metadata["height"]
    duration = metadata["duration_seconds"]
    drift_limit = MAX_CAMERA_DRIFT_FRACTION * width

    return [
        (
            "single continuous shot (no cuts)",
            not cuts,
            "no shot changes detected" if not cuts else f"cuts at {cuts[:8]} s",
        ),
        (
            "steady camera",
            camera_drift <= drift_limit,
            f"max drift {camera_drift:.1f}px (limit {drift_limit:.0f}px)",
        ),
        (
            f"duration {MIN_DURATION_SECONDS:g}-{MAX_DURATION_SECONDS:g} s",
            MIN_DURATION_SECONDS <= duration <= MAX_DURATION_SECONDS,
            f"{duration:.1f} s",
        ),
        (
            f"resolution at least {MIN_WIDTH}x{MIN_HEIGHT}",
            width >= MIN_WIDTH and height >= MIN_HEIGHT,
            f"{width}x{height}",
        ),
    ]


def read_clip(video_path):
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    analysis_frames = []
    try:
        while True:
            readable, frame = capture.read()
            if not readable:
                break
            analysis_frames.append(to_analysis_frame(frame))
    finally:
        capture.release()

    if fps <= 0 or not analysis_frames:
        raise ValueError("The video has invalid FPS or no frames.")

    metadata = {
        "fps": round(fps, 3),
        "width": width,
        "height": height,
        "frame_count": len(analysis_frames),
        "duration_seconds": len(analysis_frames) / fps,
    }
    return metadata, analysis_frames


def check_clip(video_path):
    video_path = Path(video_path)
    metadata, analysis_frames = read_clip(video_path)
    cuts = find_cuts(analysis_frames, metadata["fps"])
    drift = measure_camera_drift(analysis_frames, metadata["width"])
    requirements = evaluate_requirements(metadata, cuts, drift)
    return {
        "clip": video_path.stem,
        "sha256": file_sha256(video_path),
        **metadata,
        "cuts_seconds": cuts,
        "camera_drift_pixels": round(drift, 1),
        "requirements": [
            {"requirement": name, "passed": passed, "detail": detail}
            for name, passed, detail in requirements
        ],
        "passed": all(passed for _, passed, _ in requirements),
    }


def sources_row(report):
    """A ``sources.csv`` row with the derived fields filled in."""
    return ",".join(
        [
            report["clip"],
            "",  # split: assign before running any detector
            "", "", "",  # tournament, year, surface
            "", "",  # player_a, player_b
            "", "",  # channel, url
            "",  # interval
            f"{report['fps']:g}",
            f"{report['width']}x{report['height']}",
            f"{report['duration_seconds']:.1f}",
            "",  # events (after annotation)
            report["sha256"],
            "",  # notes
        ]
    )


def print_report(report):
    status = "PASS" if report["passed"] else "FAIL"
    print(f"{report['clip']}: {status}")
    print(
        f"  {report['width']}x{report['height']} @ {report['fps']:g} FPS, "
        f"{report['frame_count']} frames, {report['duration_seconds']:.1f} s"
    )
    for item in report["requirements"]:
        mark = "ok  " if item["passed"] else "FAIL"
        print(f"  [{mark}] {item['requirement']}: {item['detail']}")
    print(f"  sha256: {report['sha256']}")
    print("  Still to confirm by eye: full court visible, both players on court,")
    print("  singles, no replay or slow motion.")
    print("\nsources.csv row (fill in the blanks):")
    print(sources_row(report))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("videos", nargs="+", help="Candidate clip path(s).")
    parser.add_argument("--json", help="Write the reports to this JSON path.")
    args = parser.parse_args(argv)

    reports = []
    for video in args.videos:
        report = check_clip(video)
        reports.append(report)
        print_report(report)
        print()

    if args.json:
        Path(args.json).write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if all(report["passed"] for report in reports) else 1)


if __name__ == "__main__":
    main()
