# Tennis Analysis System

[![Tests](https://github.com/stoppo22/tennis-analysis-system/actions/workflows/tests.yml/badge.svg)](https://github.com/stoppo22/tennis-analysis-system/actions/workflows/tests.yml)

Computer-vision project that analyses tennis videos with Python, OpenCV,
PyTorch, and YOLO. The pipeline detects players and the ball, estimates court
keypoints, maps movement onto a mini court, identifies shot events, calculates
speed statistics, and produces an annotated video plus per-frame statistics in
CSV format.

## Project status: v1.0 release candidate

The project now includes a small, video-separated benchmark for tennis-shot
detection and a measured improvement over the original rule:

| Split | Baseline F1 | Improved F1 |
| --- | ---: | ---: |
| Development | 0.7500 | 0.8293 |
| Test | 0.5806 | 0.6875 |

On the held-out test video, this is an `18.4%` relative F1 improvement. Recall
increased from `0.6000` to `0.7333`, false negatives decreased from `6` to `4`,
and mean absolute timing error decreased from `0.0578 s` to `0.0509 s`. These
figures come from a deliberately small two-video benchmark and are not a claim
of broad generalization.

The improvement was selected using only the development video and then
evaluated once on the test video. Event evaluation uses one-to-one matching
within ±0.25 seconds and reports precision, recall, F1, false positives, false
negatives, and mean absolute timing error.

In v0.6, the shot detector's persistence and smoothing thresholds are expressed
as durations instead of fixed frame counts. They are converted using each
video's FPS, while preserving the frozen v0.5 behavior exactly at 25 FPS. This
is a frame-rate normalization change, not a new F1 improvement claim.

The implementation, automated tests, visual demo, model card, licensing, and
clean-clone setup verification are now complete. The `v1.0` tag has not been
created yet: the remaining release step is to attach the documented ball
checkpoint outside Git and verify that download from a clean clone.

See the [benchmark documentation](benchmark/README.md) for the annotation
protocol, source information, complete metrics, error analysis, and known
limitations.

## Visual demo

![Tennis Analysis System analysing Sinner vs Djokovic](docs/sinner-djokovic-wimbledon-2025-demo.gif)

This silent six-second excerpt shows the system analysing Jannik Sinner vs
Novak Djokovic in the 2025 Wimbledon semifinal. The source footage comes from
the official Wimbledon YouTube channel:
[watch the original video](https://www.youtube.com/watch?v=eoiKSfYg71o).

The excerpt was shortened, resized, muted, and modified with player and ball
detections, court keypoints, shot-event indicators, a mini court, and estimated
player statistics to demonstrate the project's technical operation. The source
footage is not presented as freely licensed and is not covered by this
repository's software licence. The complete source video and local benchmark
clip are not included in the repository.

## Version history

| Version | Commit | Main result |
| --- | --- | --- |
| `initial-baseline` | `a3bb1a0` | Tutorial-based pipeline before the evaluation and engineering work. |
| `v0.2` | `cecc0e9` | Reusable pipeline, source-video FPS, CLI, validation, safer caches, pinned dependencies, and removal of generated artifacts from the tracked tree. |
| `v0.3` | `dfd62f0` | Player-statistics logic extracted, corrected, clarified, and covered by automated tests. |
| `v0.5` | `ed1f8bc` | Video-separated benchmark, one-to-one event evaluation, development-set error analysis, and measured shot-detection improvement. |
| `v0.6` | `e65b6bf` | Shot-detection thresholds normalized by video FPS while preserving the v0.5 results at 25 FPS. |
| Post-v0.6 | `74f7430` onward | History cleanup, structured CSV export, notebook cleanup, CI, redesigned overlays, model documentation, licensing, visual demo, and clean-clone verification. |

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

### My work beyond the tutorial

Through guided development and learning, I extended the starting point with:

- a reusable CLI pipeline, validation, source-FPS handling, and
  content-addressed detection caches;
- corrected player statistics and a structured per-frame CSV export;
- a manually annotated 54-event benchmark split by source video;
- one-to-one temporal event matching and development-only error analysis that
  improved held-out shot-detection F1 by `18.4%` relative (`0.5806` to
  `0.6875`) while reducing false negatives from `6` to `4`;
- FPS-normalized detection thresholds that preserve the frozen 25 FPS results;
- 41 automated tests, GitHub Actions, and a verified clean-clone setup;
- stable player roles, redesigned overlays, a mini court, and a visual demo;
- repository-history cleanup, model documentation, and explicit licensing and
  attribution.

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

### Clean-clone verification

On 23 August 2026, commit `7b310b6` was cloned into a new temporary directory
and tested on an Intel Mac running macOS 12.7.6 with Python 3.11.9. A fresh
virtual environment was created exclusively from the README instructions and
`requirements.txt`.

The dependency installation completed successfully, `pip check` reported no
conflicts, the pinned OpenCV, PyTorch, Torchvision, and Ultralytics packages
imported correctly, all 41 automated tests passed, and `python main.py --help`
completed successfully. The CLI also reported the missing input and three
required model files clearly when run without local assets.

This verifies the clean setup, dependency set, tests, and command-line entry
point. A complete clean-clone video analysis still depends on publishing the
project-specific ball checkpoint as a v1.0 release asset and supplying the
other documented local assets.

## Required local assets

Large model weights and videos are intentionally excluded from Git. Place these
three files at the exact paths below before running the pipeline:

| Local path | Purpose | Source and status |
| --- | --- | --- |
| `yolo11l.pt` | Player detection | Official [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/) pretrained checkpoint. Ultralytics documents AGPL-3.0 and Enterprise licensing options. |
| `models/yolov11best.pt` | Tennis-ball detection | Project-specific fine-tuned checkpoint. See its [model card](docs/ball-detector-model-card.md) for training metadata, metrics, licence, and limitations. It is not currently redistributed; use the training instructions below to recreate it. |
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
the resulting `best.pt` checkpoint to `models/yolov11best.pt`. The exact local
checkpoint used by the project is documented in its
[model card](docs/ball-detector-model-card.md).

The notebook reads the Roboflow private API key from the
`ROBOFLOW_API_KEY` environment variable. Set it in the environment that starts
Jupyter; never paste it into the notebook, commit it, or use the publishable
InferenceJS key in its place. Training is separate from normal runtime setup
and can require substantially more time and compute than running the pipeline.

The cleaned notebook has been syntax-checked and its dataset validation logic
has been reviewed, but the complete dataset download and 100-epoch training run
have not yet been repeated from a fresh environment.

### Recreating the court-keypoint checkpoint

The tutorial author also provides the court-keypoint training dataset used by
`training/tennis_key_point_detector_training.ipynb`. The notebook downloads it
into the ignored `training/local_data/` directory, validates the annotations,
trains a ResNet-50 regressor, and saves the resulting checkpoint at
`models/keypoints_model.pth`.

The dataset's redistribution licence has not been verified, so neither the
archive nor its extracted files are committed. The cleaned notebook has been
syntax-checked, and its dataset loader, model output shape, and one-epoch
training/validation flow have been smoke-tested with synthetic data. The full
dataset download and 20-epoch training run have not yet been repeated.

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

By default, this creates both:

```text
output_videos/output_video.avi
output_videos/output_video_statistics.csv
```

Choose a different CSV path when needed:

```bash
python main.py \
  --input input_videos/input_video.mp4 \
  --output output_videos/output_video.avi \
  --statistics-output results/match_statistics.csv
```

The video contains detections, court keypoints, the mini court, and player
statistics. The CSV contains one row per video frame, including cumulative shot
counts and the latest and average estimated shot and player speeds. An empty
average means that no corresponding speed sample was available at that frame.
Its `frame_num` column is zero-based, so a 214-frame video uses values from 0
through 213.

When used from Python, `analyze_video()` returns a dictionary containing the
two output paths, FPS, frame count, duration, and detected shot frames.

## License and attribution

This repository is distributed under the
[GNU Affero General Public License v3.0](LICENSE), consistent with the
open-source licence used by Ultralytics YOLO code and trained models. Commercial
or proprietary uses may require a separate Ultralytics licence.

The initial pipeline was developed by following Abdullah Tarek's tutorial. The
subsequent engineering, evaluation, testing, documentation, and interface work
is separated explicitly in [NOTICE](NOTICE), together with the relevant
third-party attributions. External datasets, model weights, and video footage
retain their own terms and are not automatically covered by the repository's
software licence.

## Current limitations

- The benchmark contains only two short clips and 54 annotated in-play shots.
- Its results do not establish performance across tournaments, camera angles,
  or video qualities.
- Both benchmark clips are 25 FPS; cross-FPS behavior is covered by controlled
  trajectory tests and a local 30 FPS smoke test, not a multi-FPS benchmark.
- The benchmark videos are kept local and are not redistributed because an
  explicit reusable licence has not been verified.
- The player and ball speed estimates exported to CSV have not been evaluated
  against ground-truth speeds.
- The cleaned training notebooks have passed syntax and synthetic smoke checks,
  but their complete training runs have not yet been reproduced from scratch.
- The redistribution licence for the tutorial author's court-keypoint dataset
  has not been verified.
- Model weights, input videos, full generated videos, and detection caches are
  not stored in Git. The short compressed GIF above is the only generated-video
  excerpt included for demonstration.

## Release candidate checklist

Completed: pipeline, benchmark, measured improvement, automated tests, history
cleanup, model card, licensing, visual demo, and clean-clone setup verification.

Before creating the `v1.0` tag, the remaining required steps are:

1. attach `yolov11best.pt` to the GitHub release without adding it to Git;
2. download the asset into a clean clone and verify its SHA-256;
3. run the final local video smoke test;
4. publish the release notes and CV description using only the measured claims
   documented above.
