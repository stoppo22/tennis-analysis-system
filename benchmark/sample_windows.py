"""Pick reproducible random time windows from a long match video.

Downloading hours of footage is unnecessary, and choosing the "nice" rallies by
hand would bias the benchmark. Instead, each match gets a few random windows whose
positions are fixed by a seed derived from the match id, and every qualifying
live rally inside those windows is used.

    yt-dlp --print duration "<url>"                     # duration in seconds
    python -m benchmark.sample_windows <match_id> <duration_seconds> --url "<url>"
"""

import argparse
import hashlib
import random

DEFAULT_WINDOWS = 3
DEFAULT_LENGTH_SECONDS = 150
START_FRACTION = 0.10  # skip the introduction and warm-up
END_FRACTION = 0.95


def seed_from_match_id(match_id):
    return int(hashlib.sha256(match_id.encode("utf-8")).hexdigest()[:8], 16)


def sample_windows(
    match_id,
    duration_seconds,
    windows=DEFAULT_WINDOWS,
    length_seconds=DEFAULT_LENGTH_SECONDS,
    seed=None,
):
    """Return ``windows`` non-overlapping ``(start, end)`` pairs, sorted."""
    if windows < 1 or length_seconds <= 0:
        raise ValueError("Need at least one window of positive length.")

    low = START_FRACTION * duration_seconds
    high = END_FRACTION * duration_seconds - length_seconds
    if high <= low or (high - low) < (windows - 1) * length_seconds:
        raise ValueError("The video is too short for the requested windows.")

    rng = random.Random(seed_from_match_id(match_id) if seed is None else seed)
    chosen = []
    for _ in range(10000):
        start = rng.uniform(low, high)
        if all(abs(start - other) >= length_seconds for other in chosen):
            chosen.append(start)
            if len(chosen) == windows:
                break
    else:
        raise ValueError("Could not place non-overlapping windows.")

    return [(int(start), int(start) + int(length_seconds)) for start in sorted(chosen)]


def format_timestamp(seconds):
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def download_command(match_id, url, number, start, end):
    return (
        'yt-dlp -f "bv*[height<=1080]" --force-keyframes-at-cuts '
        f'--download-sections "*{format_timestamp(start)}-{format_timestamp(end)}" '
        f'-o "input_videos/benchmark/raw/{match_id}_w{number}.%(ext)s" "{url}"'
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("match_id")
    parser.add_argument("duration_seconds", type=float)
    parser.add_argument("--windows", type=int, default=DEFAULT_WINDOWS)
    parser.add_argument("--length-seconds", type=int, default=DEFAULT_LENGTH_SECONDS)
    parser.add_argument("--url", default="<url>")
    args = parser.parse_args(argv)

    selected = sample_windows(
        args.match_id, args.duration_seconds, args.windows, args.length_seconds
    )
    print(f"{args.match_id}: {len(selected)} windows of {args.length_seconds} s\n")
    for number, (start, end) in enumerate(selected, start=1):
        print(f"w{number}  {format_timestamp(start)} -> {format_timestamp(end)}")
        print(f"    {download_command(args.match_id, args.url, number, start, end)}")


if __name__ == "__main__":
    main()
