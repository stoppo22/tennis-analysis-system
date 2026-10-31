"""Find uninterrupted segments (candidate rallies) in a full-match video.

A broadcast cuts to close-ups between points, so the long uninterrupted shots in
a full match are mostly points played from the standard camera. The script
detects shot changes, lists the segments between them, saves three thumbnails
per segment for a quick visual check, and prints an ``ffmpeg`` command for each.

    python -m benchmark.find_rallies input_videos/benchmark/raw/<match>.mp4 \
        --thumbnails input_videos/benchmark/candidates/<match>

Replays and slow-motion shots of earlier points are also uninterrupted
segments, so every candidate must be inspected before use.
"""

import argparse
from pathlib import Path

import cv2

from benchmark.check_clip import (
    CUT_CORRELATION_THRESHOLD,
    CUT_MEAN_DIFFERENCE_THRESHOLD,
    _histogram,
    to_analysis_frame,
)

DEFAULT_MIN_SECONDS = 8.0
DEFAULT_MAX_SECONDS = 60.0
DEFAULT_MARGIN_SECONDS = 0.5


def scan_cuts(video_path, stride=2):
    """Return ``(cut_times, duration_seconds, fps)`` for the whole video.

    Only every ``stride``-th frame is compared, so a cut is located within
    ``stride`` frames; the margin applied to each segment absorbs this.
    """
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise ValueError("The video has an invalid frame rate.")

    cuts = []
    previous = previous_histogram = None
    index = 0
    last_index = -1
    try:
        while True:
            if not capture.grab():
                break
            last_index = index
            if index % stride == 0:
                readable, frame = capture.retrieve()
                if not readable:
                    break
                analysis = to_analysis_frame(frame)
                histogram = _histogram(analysis)
                if previous is not None:
                    correlation = cv2.compareHist(
                        previous_histogram, histogram, cv2.HISTCMP_CORREL
                    )
                    difference = float(cv2.mean(cv2.absdiff(analysis, previous))[0])
                    if (
                        correlation < CUT_CORRELATION_THRESHOLD
                        or difference > CUT_MEAN_DIFFERENCE_THRESHOLD
                    ):
                        cuts.append(index / fps)
                previous, previous_histogram = analysis, histogram
            index += 1
    finally:
        capture.release()

    return cuts, (last_index + 1) / fps, fps


def segments_from_cuts(
    cut_times,
    duration_seconds,
    min_seconds=DEFAULT_MIN_SECONDS,
    max_seconds=DEFAULT_MAX_SECONDS,
    margin_seconds=DEFAULT_MARGIN_SECONDS,
):
    """Segments between cuts, trimmed by a margin, kept if long enough.

    Segments longer than ``max_seconds`` are returned cut to that length from the
    start, since a benchmark clip should be one point (or a few).
    """
    boundaries = [0.0] + sorted(cut_times) + [duration_seconds]
    segments = []
    for start, end in zip(boundaries, boundaries[1:]):
        trimmed_start = start + (margin_seconds if start > 0 else 0.0)
        trimmed_end = end - (margin_seconds if end < duration_seconds else 0.0)
        length = trimmed_end - trimmed_start
        if length >= min_seconds:
            segments.append(
                {
                    "start": round(trimmed_start, 2),
                    "end": round(min(trimmed_end, trimmed_start + max_seconds), 2),
                    "duration": round(min(length, max_seconds), 2),
                }
            )
    return segments


def format_timestamp(seconds):
    whole = int(seconds)
    return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d}"


def save_thumbnails(video_path, segment, directory, number):
    """Save the first, middle and last frame of a segment side by side."""
    capture = cv2.VideoCapture(str(video_path))
    frames = []
    try:
        for fraction in (0.05, 0.5, 0.95):
            seconds = segment["start"] + fraction * (segment["end"] - segment["start"])
            capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
            readable, frame = capture.read()
            if readable:
                frames.append(cv2.resize(frame, (480, 270)))
    finally:
        capture.release()
    if not frames:
        return None
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"candidate_{number:03d}_{format_timestamp(segment['start']).replace(':', '-')}.jpg"
    cv2.imwrite(str(path), cv2.hconcat(frames))
    return path


def ffmpeg_command(video_path, segment, output_name):
    return (
        f"ffmpeg -ss {segment['start']:.2f} -to {segment['end']:.2f} "
        f"-i {video_path} -an -c:v libx264 -crf 18 -preset slow "
        f"input_videos/benchmark/{output_name}.mp4"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("video", help="Full-match video file.")
    parser.add_argument("--min-seconds", type=float, default=DEFAULT_MIN_SECONDS)
    parser.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS)
    parser.add_argument("--margin-seconds", type=float, default=DEFAULT_MARGIN_SECONDS)
    parser.add_argument("--stride", type=int, default=2, help="Compare every Nth frame.")
    parser.add_argument("--thumbnails", help="Directory for a three-frame preview per candidate.")
    parser.add_argument("--limit", type=int, default=40, help="Maximum candidates to list.")
    args = parser.parse_args(argv)

    cuts, duration, fps = scan_cuts(args.video, args.stride)
    segments = segments_from_cuts(
        cuts, duration, args.min_seconds, args.max_seconds, args.margin_seconds
    )
    print(
        f"{args.video}: {format_timestamp(duration)} at {fps:g} FPS, "
        f"{len(cuts)} cuts, {len(segments)} uninterrupted segments of at least "
        f"{args.min_seconds:g} s\n"
    )
    stem = Path(args.video).stem
    for number, segment in enumerate(segments[: args.limit], start=1):
        print(
            f"#{number:03d}  {format_timestamp(segment['start'])} -> "
            f"{format_timestamp(segment['end'])}  ({segment['duration']:.1f} s)"
        )
        if args.thumbnails:
            preview = save_thumbnails(args.video, segment, args.thumbnails, number)
            if preview:
                print(f"      preview: {preview}")
        print(f"      {ffmpeg_command(args.video, segment, f'{stem}_rally_{number:02d}')}")


if __name__ == "__main__":
    main()
