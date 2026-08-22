# Tennis-ball detector model card

## Model overview

This project uses a fine-tuned Ultralytics YOLO11l detector to locate the
tennis ball in individual video frames. The model receives an image and
produces bounding boxes, confidence scores, and the single class
`tennis ball`. Its detections are later interpolated and processed by the
analysis pipeline; the model itself does not detect racket contacts, calculate
speeds, or assign shots to players.

The checkpoint was produced through the tutorial-based training workflow used
by this project. The YOLO architecture was not designed specifically for this
repository. The cleaned training notebook records how to reproduce the
fine-tuning procedure, but the full run has not been repeated since the
notebook cleanup.

## Checkpoint identity

| Field | Value |
| --- | --- |
| Expected local path | `models/yolov11best.pt` |
| File size | 51,176,594 bytes |
| SHA-256 | `1f74aea3f7e84ccfbf61d0633d3f0d9713b20f2a7709771b8f9afa426a315d8c` |
| Task | Object detection |
| Classes | One: `tennis ball` |
| Base checkpoint | `yolo11l.pt` |
| Ultralytics version recorded in the checkpoint | `8.3.179` |
| Checkpoint date | 2025-08-15 |

The checkpoint remains outside the Git history and is distributed as a
[`v1.0` release asset](https://github.com/stoppo22/tennis-analysis-system/releases/download/v1.0/yolov11best.pt).
It can also be recreated with
`training/tennis_ball_detector_training.ipynb`.

## Training data

Training uses version 6 of Viren Dhanwani's
[Tennis Ball Detection dataset](https://universe.roboflow.com/viren-dhanwani/tennis-ball-detection/dataset/6):

- 578 images;
- one annotated class: `tennis ball`;
- YOLO11 export format;
- no augmentation recorded in the exported dataset metadata;
- dataset licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

The dataset is downloaded locally through Roboflow and is not committed to
this repository. Its original author, source, and licence must remain
attributed when the dataset is reused.

## Recorded training configuration

The checkpoint metadata and cleaned notebook agree on the main settings:

| Parameter | Value |
| --- | ---: |
| Epochs | 100 |
| Image size | 640 px |
| Batch size | 16 |
| Seed | 0 |
| Deterministic mode | Enabled |
| Patience | 100 |

The checkpoint records automatic device selection, so the exact training
hardware is not established by the saved metadata. Exact weights may differ
when the training is repeated on another environment.

## Checkpoint-saved validation metrics

These values are stored inside the local best checkpoint:

| Metric | Recorded value |
| --- | ---: |
| Precision | 0.84348 |
| Recall | 0.47525 |
| mAP@0.50 | 0.64840 |
| mAP@0.50:0.95 | 0.27659 |
| Validation box loss | 1.75397 |
| Validation classification loss | 0.99739 |
| Validation DFL loss | 0.71927 |

These are detector metrics from the dataset validation workflow. They have not
been independently reproduced after the notebook cleanup and must not be
confused with the project's shot-event benchmark. The shot-event F1 measures
the later temporal event detector after ball interpolation and post-processing.

## Intended use

The model is intended for educational, experimental analysis of broadcast-like
tennis footage with a visible court and ball. It is used as one component of
this repository's end-to-end pipeline.

It is not validated for officiating, line calling, professional performance
assessment, safety-critical decisions, or general object detection outside the
single tennis-ball class.

## Known limitations

- The training dataset is small and its validation recall is limited.
- The ball can be missed during motion blur, occlusion, compression artifacts,
  low contrast, or scoreboard overlays.
- Performance has not been established across tournaments, court surfaces,
  camera angles, resolutions, or frame rates.
- Downstream interpolation can fill short detection gaps, but it can also
  propagate inaccurate detections.
- The project benchmark contains only two local 25 FPS videos and evaluates
  shot events, not raw ball-detection boxes.
- Ball-speed estimates have not been evaluated against ground-truth speed.

## Licence and attribution

The checkpoint records the Ultralytics AGPL-3.0 licence. Ultralytics also offers
commercial licensing for uses that do not follow the open-source terms. The
repository is distributed under AGPL-3.0, while the training dataset is
provided separately under CC BY 4.0. See [LICENSE](../LICENSE) and
[NOTICE](../NOTICE) for the complete project attribution and third-party
summary.
