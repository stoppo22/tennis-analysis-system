# Tennis Analysis System

Computer-vision project that analyses tennis videos with Python, OpenCV,
PyTorch, and YOLO. The pipeline detects players and the ball, estimates court
keypoints, maps movement onto a mini court, identifies shot events, calculates
speed statistics, and produces an annotated video.

## Project status: v0.6

The project now includes a small, video-separated benchmark for tennis-shot
detection and a measured improvement over the original rule:

| Split | Baseline F1 | Improved F1 |
| --- | ---: | ---: |
| Development | 0.7500 | 0.8293 |
| Test | 0.5806 | 0.6875 |

The improvement was selected using only the development video and then
evaluated once on the test video. Event evaluation uses one-to-one matching
within ±0.25 seconds and reports precision, recall, F1, false positives, false
negatives, and mean absolute timing error.

In v0.6, the shot detector's persistence and smoothing thresholds are expressed
as durations instead of fixed frame counts. They are converted using each
video's FPS, while preserving the frozen v0.5 behavior exactly at 25 FPS. This
is a frame-rate normalization change, not a new F1 improvement claim.

See the [benchmark documentation](benchmark/README.md) for the annotation
protocol, source information, complete metrics, error analysis, and known
limitations.

## Version history

| Version | Commit | Main result |
| --- | --- | --- |
| `initial-baseline` | `a3bb1a0` | Tutorial-based pipeline before the evaluation and engineering work. |
| `v0.2` | `cecc0e9` | Reusable pipeline, source-video FPS, CLI, validation, safer caches, pinned dependencies, and removal of generated artifacts from the tracked tree. |
| `v0.3` | `dfd62f0` | Player-statistics logic extracted, corrected, clarified, and covered by automated tests. |
| `v0.5` | `ed1f8bc` | Video-separated benchmark, one-to-one event evaluation, development-set error analysis, and measured shot-detection improvement. |
| `v0.6` | `e65b6bf` | Shot-detection thresholds normalized by video FPS while preserving the v0.5 results at 25 FPS. |
| Post-v0.6 | `74f7430` onward | Repository history cleaned, training notebooks sanitized, and local asset setup documented in preparation for v1.0. |

There is intentionally no `v0.4` tag. The benchmark implementation and the
measured v0.5 improvement were committed together, so the repository does not
contain a separate, honest v0.4 snapshot to tag retroactively.

## Project origin

The initial pipeline was built by following a YouTube tutorial. The current
work extends that starting point through pipeline validation, safer detection
caching, automated tests, a reproducible evaluation workflow, manual benchmark
annotations, development-set error analysis, and a quantitatively tested shot
detection improvement. The shot-event thresholds have also been normalized for
different video frame rates.

The tutorial baseline and its original pretrained court model are available in
[Abdullah Tarek's tennis analysis repository](https://github.com/abdullahtarek/tennis_analysis).

## Local setup

Python 3.11 is the tested version for this project. From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
mkdir -p models input_videos output_videos
```

The analysis must currently be launched from the repository root because the
model paths are fixed relative to that directory.

## Required local assets

Large model weights and videos are intentionally excluded from Git. Place these
three files at the exact paths below before running the pipeline:

| Local path | Purpose | Source and status |
| --- | --- | --- |
| `yolo11l.pt` | Player detection | Official [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/) pretrained checkpoint. Ultralytics documents AGPL-3.0 and Enterprise licensing options. |
| `models/yolov11best.pt` | Tennis-ball detection | Project-specific fine-tuned checkpoint. It is not currently redistributed; use the training instructions below to recreate it. |
| `models/keypoints_model.pth` | Court keypoint prediction | Download the [pretrained court model linked by the tutorial author](https://drive.google.com/file/d/1QrTOF1ToQ4plsSZbkBs3zOLkVt3MBlta/view?usp=sharing) and rename it exactly. Its redistribution licence has not been verified, so the file is kept local. |

Download the official player detector through the pinned Ultralytics package:

```bash
python -c 'from ultralytics import YOLO; YOLO("yolo11l.pt")'
```

Reference SHA-256 checksums for the exact local weights used during development
and evaluation are:

```text
9ebd0e09d59811db4b1d61e2bc6730649608b1ac47f8dd01e2da6bca7c20023f  yolo11l.pt
1f74aea3f7e84ccfbf61d0633d3f0d9713b20f2a7709771b8f9afa426a315d8c  models/yolov11best.pt
fe166be4ebc9ca6fa1278cea252028fd242ef20bc593554c5fa2d98d82799962  models/keypoints_model.pth
```

On macOS, verify them with:

```bash
shasum -a 256 yolo11l.pt models/yolov11best.pt models/keypoints_model.pth
```

### Recreating the ball checkpoint

The ball-training notebook uses version 6 of Viren Dhanwani's
[Tennis Ball Detection dataset](https://universe.roboflow.com/viren-dhanwani/tennis-ball-detection/dataset/6),
published under CC BY 4.0. Open
`training/tennis_ball_detector_training.ipynb`, train the YOLO11 model, and copy
the resulting `best.pt` checkpoint to `models/yolov11best.pt`.

The notebook reads the Roboflow private API key from the
`ROBOFLOW_API_KEY` environment variable. Set it in the environment that starts
Jupyter; never paste it into the notebook, commit it, or use the publishable
InferenceJS key in its place. Training is separate from normal runtime setup
and can require substantially more time and compute than running the pipeline.

Input videos must be supplied by the user and placed under `input_videos/` or
passed with `--input`. Use footage you own or have permission to use. Generated
videos go under `output_videos/`; detection caches are created under
`tracker_stubs/`. All of these local artifacts remain ignored by Git.

## Run the analysis

```bash
python main.py \
  --input input_videos/input_video.mp4 \
  --output output_videos/output_video.avi
```

The output is an annotated video containing detections, court keypoints, the
mini court, and player statistics.

## Current limitations

- The benchmark contains only two short clips and 54 annotated in-play shots.
- Its results do not establish performance across tournaments, camera angles,
  or video qualities.
- Both benchmark clips are 25 FPS; cross-FPS behavior is covered by controlled
  trajectory tests and a local 30 FPS smoke test, not a multi-FPS benchmark.
- The benchmark videos are kept local and are not redistributed because an
  explicit reusable licence has not been verified.
- Model weights, input videos, generated outputs, and detection caches are not
  stored in Git.

## Next milestone

Before v1.0, the repository history must be cleaned of old binary artifacts.
The final milestone will also add a short demo, final verification, version
history, and a CV-ready project description.
