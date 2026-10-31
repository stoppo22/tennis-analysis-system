"""Run a ball-detection model over clips and store the detections as CSV.

The output has the format of ``benchmark/detections/<clip>.csv``, so any model can
be scored with ``benchmark.evaluate_ball_detectors`` and used by the shot-event
experiments without re-running it.

    python -m benchmark.export_model_detections --weights models/yolov11best.pt \
        --videos input_videos/benchmark/*.mp4 --output-dir runs/yolo11l/detections

``--selection`` decides which box is kept when a frame has several candidates:
``last`` reproduces the pipeline (the last box in the result), ``confidence`` keeps
the most confident one.
"""

import argparse
from pathlib import Path

import cv2

from benchmark.detections import save_detections_csv

DEFAULT_CONFIDENCE = 0.15  # same threshold as the pipeline
SELECTIONS = ("last", "confidence")


def select_box(boxes, confidences, selection):
    """Pick one box from the candidates of a frame, or ``None`` if there are none."""
    if selection not in SELECTIONS:
        raise ValueError(f"Selection must be one of {SELECTIONS}.")
    if len(boxes) != len(confidences):
        raise ValueError("Boxes and confidences must have the same length.")
    if not boxes:
        return None
    if selection == "last":
        return list(boxes[-1])
    best = max(range(len(boxes)), key=lambda index: confidences[index])
    return list(boxes[best])


def export_video(video_path, weights, output_path, imgsz, confidence, selection):
    from ultralytics import YOLO  # imported here: heavy and optional

    model = YOLO(str(weights))
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    detections = []
    try:
        while True:
            readable, frame = capture.read()
            if not readable:
                break
            result = model.predict(frame, conf=confidence, imgsz=imgsz, verbose=False)[0]
            boxes = result.boxes.xyxy.tolist()
            scores = result.boxes.conf.tolist()
            box = select_box(boxes, scores, selection)
            detections.append({1: box} if box else {})
    finally:
        capture.release()

    save_detections_csv(detections, output_path)
    found = sum(1 for entry in detections if entry)
    print(f"{video_path}: {len(detections)} frames, {found} with a detection -> {output_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--weights", required=True)
    parser.add_argument("--videos", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    parser.add_argument("--selection", choices=SELECTIONS, default="last")
    args = parser.parse_args(argv)

    for video in args.videos:
        output = Path(args.output_dir) / f"{Path(video).stem}.csv"
        export_video(video, args.weights, output, args.imgsz, args.confidence, args.selection)


if __name__ == "__main__":
    main()
