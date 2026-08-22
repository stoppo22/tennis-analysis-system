import argparse
import csv
from pathlib import Path

import cv2


def frame_to_seconds(frame_number, fps):
    if fps <= 0:
        raise ValueError("FPS must be greater than zero.")
    return frame_number / fps


def add_shot_frame(shot_frames, frame_number):
    if frame_number in shot_frames:
        return False

    shot_frames.append(frame_number)
    return True


def save_annotations(output_path, shot_frames, fps):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["frame", "time_seconds"],
            lineterminator="\n",
        )
        writer.writeheader()
        for frame_number in sorted(shot_frames):
            writer.writerow(
                {
                    "frame": frame_number,
                    "time_seconds": f"{frame_to_seconds(frame_number, fps):.6f}",
                }
            )


def draw_status(frame, frame_number, fps, annotation_count, paused):
    display_frame = frame.copy()
    status = "PAUSED" if paused else "PLAYING"
    lines = [
        f"{status} | frame {frame_number} | {frame_to_seconds(frame_number, fps):.3f} s",
        f"Recorded shots: {annotation_count}",
        "SPACE play/pause | A/D previous/next | H hit | U undo | S save | Q save+quit",
    ]

    for index, line in enumerate(lines):
        y = 30 + index * 30
        cv2.putText(
            display_frame,
            line,
            (15, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 0),
            4,
            cv2.LINE_AA,
        )
        cv2.putText(
            display_frame,
            line,
            (15, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    return display_frame


def annotate_video(video_path, output_path):
    video = cv2.VideoCapture(str(video_path))
    if not video.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = video.get(cv2.CAP_PROP_FPS)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or frame_count <= 0:
        video.release()
        raise ValueError("The video has invalid FPS or no frames.")

    shot_frames = []
    paused = True
    window_name = "Shot annotation"

    print(f"Video: {video_path}")
    print(f"Frames: {frame_count} | FPS: {fps:.3f}")
    print("Press H on each in-play racket-ball contact, then Q to save and quit.")

    try:
        while True:
            readable, frame = video.read()
            if not readable:
                break

            frame_number = int(video.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            display_frame = draw_status(
                frame, frame_number, fps, len(shot_frames), paused
            )
            cv2.imshow(window_name, display_frame)

            delay_ms = 0 if paused else max(1, round(1000 / fps))
            key = cv2.waitKey(delay_ms) & 0xFF

            if key == ord(" "):
                paused = not paused
            elif key in (ord("a"), ord("A")):
                paused = True
                video.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_number - 1))
            elif key in (ord("d"), ord("D")):
                paused = True
            elif key in (ord("h"), ord("H")):
                paused = True
                if add_shot_frame(shot_frames, frame_number):
                    print(f"Added frame {frame_number}")
            elif key in (ord("u"), ord("U")) and shot_frames:
                removed_frame = shot_frames.pop()
                print(f"Removed frame {removed_frame}")
            elif key in (ord("s"), ord("S")):
                save_annotations(output_path, shot_frames, fps)
                print(f"Saved {len(shot_frames)} shots to {output_path}")
            elif key in (ord("q"), ord("Q")):
                save_annotations(output_path, shot_frames, fps)
                print(f"Saved {len(shot_frames)} shots to {output_path}")
                return

        save_annotations(output_path, shot_frames, fps)
        print(f"Reached the end. Saved {len(shot_frames)} shots to {output_path}")
    finally:
        video.release()
        cv2.destroyAllWindows()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mark in-play racket-ball contacts in a tennis clip."
    )
    parser.add_argument("--video", required=True, help="Path to the local video clip.")
    parser.add_argument("--output", required=True, help="Path to the annotation CSV.")
    return parser.parse_args()


def main():
    args = parse_args()
    annotate_video(args.video, args.output)


if __name__ == "__main__":
    main()
