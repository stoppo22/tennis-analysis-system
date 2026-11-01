# Tennis Analysis System

[![Tests](https://github.com/stoppo22/tennis-analysis-system/actions/workflows/tests.yml/badge.svg)](https://github.com/stoppo22/tennis-analysis-system/actions/workflows/tests.yml)

Computer-vision pipeline that analyses broadcast tennis footage with Python,
OpenCV, PyTorch, and YOLO. Given a video, it detects the players and the ball,
estimates the court keypoints, maps movement onto a mini court, detects shot
events, estimates speeds, and produces an annotated video plus a per-frame
statistics CSV.

![Tennis Analysis System analysing Sinner vs Djokovic](docs/sinner-djokovic-wimbledon-2025-demo.gif)

This silent six-second excerpt shows the system analysing Jannik Sinner vs
Novak Djokovic in the 2025 Wimbledon semifinal. The source footage comes from
the official Wimbledon YouTube channel:
[watch the original video](https://www.youtube.com/watch?v=eoiKSfYg71o). It was
shortened, resized, muted, and overlaid with detections to demonstrate the
system. The source footage is not freely licensed and is not covered by this
repository's software licence; the full video and benchmark clips are not
included.

## What it does

```text
video ─► player detection (YOLO11 + tracking) ─┐
      ─► ball detection (fine-tuned YOLO11) ───┼─► shot-event detection ─► statistics
      ─► court keypoints (ResNet-50 regressor) ┘        │                      │
                                                        └──► mini court ◄──────┘
                                                               │
                                              annotated video + per-frame CSV
```

## Results

Shot-event detection (the instants at which a player hits the ball) is evaluated on
a hand-annotated benchmark split by source match. Events are matched one-to-one
within ±0.25 s, and intervals are 95% block-bootstrap intervals.

### Held-out test: 28 clips, 208 contacts, 4 matches

The test clips were sampled at random from four full matches (clay, hard, grass and
indoor hard; 25, 50 and 59.94 FPS), annotated by hand and **frozen before any
detector was run on them**. The two methods and their parameters were fixed on
development data and each was evaluated **once**:

| Method | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| Original rule, 1.0 s persistence | 0.489 [0.374, 0.594] | 0.317 [0.236, 0.402] | 0.385 [0.293, 0.471] |
| Persistence rule, 0.72 s (`persistence_18`) | 0.458 [0.363, 0.548] | 0.466 [0.376, 0.555] | 0.462 [0.375, 0.544] |
| **Alternating-swing detector (`swing_v1`)** | **0.587 [0.500, 0.670]** | **0.567 [0.484, 0.649]** | **0.577 [0.499, 0.651]** |

Paired difference, `swing_v1` minus `persistence_18` (same resampled blocks):
precision **+0.130 [+0.058, +0.201]**, recall **+0.101 [+0.046, +0.160]**, F1
**+0.115 [+0.063, +0.168]**. The intervals exclude zero. F1 is higher in all four
matches and on 21 of the 28 clips (lower on 5, equal on 2).

How to read this:

- **The gain is established on unseen data**, and it matches the direction seen on
  development data. It is a comparison of two shot-event rules on the same ball
  detections, not a claim about tennis analysis in general.
- **Absolute performance is modest.** F1 is 0.58, well below the development
  clips (0.79-0.86). The ball model detects the ball in only 47.5% of the test
  frames (66% in one match, 28-34% in the other three), and event detection
  inherits that. The reason for the drop was not investigated.
- **Timing is less accurate**: mean timing error of matched events is 0.117 s for
  `swing_v1` against 0.077 s for `persistence_18`.
- **Limits of the data:** one annotator and a first pass only (the second pass that
  bounds annotation noise is not done yet), four matches whose clips are not
  independent, and two matches share a player.

Full protocol, amendments, selection record and the pre-registered development
study: [benchmark/README.md](benchmark/README.md),
[benchmark/CLIP_SELECTION.md](benchmark/CLIP_SELECTION.md) and
[benchmark/EXPERIMENT_swing_detector.md](benchmark/EXPERIMENT_swing_detector.md). The
evaluation design is summarised in
[docs/evaluation-methodology.md](docs/evaluation-methodology.md), and the ball
detector in its [model card](docs/ball-detector-model-card.md).

### Removing static detections (second look at the test)

The ball model often reports a mark on the clay as the ball (in six of nine
Roland-Garros clips one 16-pixel spot holds 22-63% of all detections). Dropping
detections that stay in the same place for about a second, a rule fixed before
evaluation with no tuned parameters, raised F1 on the test split from 0.577 to 0.659
for `swing_v1` (paired difference +0.082 [+0.020, +0.150]) and from 0.462 to 0.589 for
`persistence_18` (+0.127 [+0.061, +0.202]). The decision to try it was made on
development clips, and this test result is a **second use** of a test that was
already evaluated once, so it is not independent of the first. The filter is available
as `--suppress-static` in `benchmark.predict_from_detections` and is not yet part of
the pipeline. Details: [benchmark/EXPERIMENT_static_detections.md](benchmark/EXPERIMENT_static_detections.md).

### Development results

On the six development clips (89 contacts, two matches) the same comparison under a
pre-registered leave-one-clip-out protocol gave an F1 gain of +0.046 [-0.020, +0.120]
with a clear precision gain, which the test above then confirmed. The original v0.5
benchmark (two clips, 54 events) showed F1 0.7500 to 0.8293 and 0.5806 to 0.6875 for
the 25-frame and 18-frame persistence rules; those clips are now development data.

## Quick start

Python 3.11 is the tested version. From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
mkdir -p models input_videos output_videos
```

The editable install provides the `tennis-analysis` command and the
`tennis_analysis` package. Model locations default to the paths below, relative
to the working directory, and can be overridden with `--player-model`,
`--ball-model`, `--court-model` and `--cache-dir`.

### Required model files

Three model files are required and are not stored in Git:

| Local path | Purpose |
| --- | --- |
| `yolo11l.pt` | Player detection (official Ultralytics checkpoint) |
| `models/yolov11best.pt` | Ball detection ([`v1.0` release asset](https://github.com/stoppo22/tennis-analysis-system/releases/download/v1.0/yolov11best.pt)) |
| `models/keypoints_model.pth` | Court keypoints (tutorial author's model, kept local) |

Download links, SHA-256 checksums, and instructions for retraining are in
[docs/assets-and-training.md](docs/assets-and-training.md).

### Run the analysis

Supply a video you own or have permission to use:

```bash
tennis-analysis \
  --input input_videos/input_video.mp4 \
  --output output_videos/output_video.avi
```

`python -m tennis_analysis` is equivalent. Two options change how shots are found:

- `--shot-detector swing` selects the alternating-swing detector (default:
  `persistence`, the original rule);
- `--suppress-static` removes ball detections that stay in the same place for about a
  second, which are usually marks on the court mistaken for the ball.

On the held-out test clips the combination `swing` plus `--suppress-static` gave the
best F1 (see [Results](#results)). Both are off by default so that existing behaviour
does not change; a complete run of the pipeline with both options on a 271-frame clip
produced a video and a statistics CSV with one row per frame.

This creates the annotated video and, next to it,
`output_video_statistics.csv`. Use `--statistics-output` to choose another CSV
path.

The CSV has one row per frame (`frame_num` is zero-based), with cumulative shot
counts and the latest and average estimated shot and player speeds. An empty
average means no speed sample was available yet. From Python, `analyze_video()`
returns a dictionary with the output paths, FPS, frame count, duration, and
detected shot frames.

### Run the tests and the linter

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m unittest discover -s tests -v
```

The same checks run in GitHub Actions on every push and pull request.

### Repository layout

| Path | Content |
| --- | --- |
| `tennis_analysis/` | Installable package: pipeline, CLI, trackers, court detector, mini court, utilities |
| `benchmark/` | Evaluation tooling, annotations, stored ball detections, predictions and experiment results |
| `tests/` | Automated tests |
| `training/` | Notebooks that recreate the ball and court-keypoint models |
| `docs/` | Model card, assets, project history |

## Project origin and attribution

The initial pipeline was built by following
[Abdullah Tarek's tennis analysis tutorial](https://github.com/abdullahtarek/tennis_analysis),
including the pretrained court-keypoint model. My work on top of it covers the
reusable CLI pipeline with validation and content-addressed caches, corrected
statistics and CSV export, the manually annotated benchmark, the evaluation
code, the error analysis and measured shot-detection improvement,
FPS-normalized thresholds, tests and CI, and the overlays. The full list and
version history are in [docs/project-history.md](docs/project-history.md); the
split between tutorial and project-specific work is also stated in
[NOTICE](NOTICE).

## Current limitations

- The test split has 28 clips, 208 contacts and four matches, annotated by one
  person in a first pass; results do not establish performance across other
  tournaments, camera angles, or video qualities.
- Both shot detectors rely on the vertical motion of the ball in image space,
  and the ball model detects the ball in only 47.5% of the test frames (28-34% in
  three of the four matches), so gaps are interpolated and event detection is
  limited by ball detection. `swing_v1` times events about 0.04 s less accurately
  than the persistence rule.
- Court keypoints are estimated once, on the first frame, so the camera is
  assumed static. Broadcast cuts and zooms are not handled.
- Player and ball speed estimates are derived from mini-court coordinates and
  have not been evaluated against ground-truth speeds. A ball in flight
  projected onto the court plane introduces systematic error.
- The training notebooks have passed syntax and synthetic smoke checks, but
  full training runs have not been reproduced from scratch.
- The redistribution licence of the court-keypoint model and dataset has not
  been verified, so that model must be downloaded separately.
- Model weights, input videos, full generated videos, and detection caches are
  not stored in Git.

## Roadmap

1. Complete the second annotation pass on the test clips to measure the agreement
   between two annotators, which bounds what any detector can reach.
2. Recover the timing accuracy of `swing_v1` and add player proximity to reject
   shifted events; both need a new fresh test split.
3. Evaluate and improve ball detection and tracking: the ball is seen in under half
   of the test frames and this limits every method. Compare detector architectures
   and input resolution with the same protocol.
4. Reconstruct trajectories in metres via the court homography and validate
   speeds against broadcast serve-speed readouts.
5. Packaging: `pyproject.toml`, Docker, end-to-end test, and throughput numbers.

## License

Distributed under the [GNU Affero General Public License v3.0](LICENSE),
consistent with the licence of Ultralytics YOLO code and trained models.
Commercial or proprietary use may require a separate Ultralytics licence.
Datasets, model weights, and video footage retain their own terms; see
[NOTICE](NOTICE).
