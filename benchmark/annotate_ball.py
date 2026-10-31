"""Mark the ball centre on a seeded random sample of frames of a clip.

    python -m benchmark.annotate_ball --video clip.mp4 --output ball_annotations/clip.csv

Controls: click the ball centre; ``N`` the ball is not visible; ``U`` undo the
previous frame; ``S`` save; ``Q`` save and quit. The same frames are offered every
time for a given clip name, and an existing output file is resumed, so the work can
be split across sessions.
"""

import argparse
import hashlib
from pathlib import Path

import cv2

from benchmark.ball_detection import (
    load_ball_annotations,
    sample_frames,
    save_ball_annotations,
)

DEFAULT_FRAME_COUNT = 75
WINDOW_NAME = "Ball annotation"


def seed_for_clip(clip_name):
    return int(hashlib.sha256(clip_name.encode("utf-8")).hexdigest()[:8], 16)


def next_unannotated(sample, annotations):
    """First sampled frame without an annotation, or ``None`` when finished."""
    for frame in sample:
        if frame not in annotations:
            return frame
    return None


def annotate_video(video_path, output_path, count):
    video = cv2.VideoCapture(str(video_path))
    if not video.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    sample = sample_frames(frame_count, count, seed_for_clip(Path(video_path).stem))

    output_path = Path(output_path)
    annotations = load_ball_annotations(output_path) if output_path.is_file() else {}
    history = []
    clicked = {}

    def on_mouse(event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked["position"] = (float(x), float(y))

    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)
    print(f"{len(sample)} frames sampled, {len(annotations)} already annotated.")

    try:
        while True:
            frame_number = next_unannotated(sample, annotations)
            if frame_number is None:
                print("All sampled frames are annotated.")
                break

            video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            readable, frame = video.read()
            if not readable:
                raise ValueError(f"Could not read frame {frame_number}.")

            done = len([f for f in sample if f in annotations])
            label = f"frame {frame_number} ({done + 1}/{len(sample)})  click ball | N not visible | U undo | Q save+quit"
            clicked.pop("position", None)

            while "position" not in clicked:
                display = frame.copy()
                cv2.putText(display, label, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(display, label, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.imshow(WINDOW_NAME, display)
                key = cv2.waitKey(30) & 0xFF
                if key in (ord("n"), ord("N")):
                    annotations[frame_number] = None
                    history.append(frame_number)
                    break
                if key in (ord("u"), ord("U")) and history:
                    annotations.pop(history.pop(), None)
                    break
                if key in (ord("s"), ord("S")):
                    save_ball_annotations(output_path, annotations)
                if key in (ord("q"), ord("Q")):
                    save_ball_annotations(output_path, annotations)
                    print(f"Saved {len(annotations)} annotations to {output_path}")
                    return
            else:
                annotations[frame_number] = clicked["position"]
                history.append(frame_number)

        save_ball_annotations(output_path, annotations)
        print(f"Saved {len(annotations)} annotations to {output_path}")
    finally:
        video.release()
        cv2.destroyAllWindows()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--count", type=int, default=DEFAULT_FRAME_COUNT)
    args = parser.parse_args(argv)
    annotate_video(args.video, args.output, args.count)


if __name__ == "__main__":
    main()
