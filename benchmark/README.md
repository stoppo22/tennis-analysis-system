# Small tennis-shot benchmark

This preliminary benchmark contains two locally stored clips from different
source videos. Video files are ignored by Git and are not redistributed.

## Development split

- Local clip: `development_australian_open_2024_sinner_medvedev_rally_01.mp4`
- Match: Jannik Sinner vs Daniil Medvedev, 2024 Australian Open final
- Source: official Australian Open YouTube channel
- URL: https://www.youtube.com/watch?v=qvY9Jl7CI7U
- Source interval: 00:01–00:53
- Clip duration: 52.0 seconds
- Resolution and frame rate: 1280×720, 25 FPS
- Source description identifies the point as a 39-shot rally.

## Test split

- Local clip: `test_wimbledon_2025_sinner_djokovic_rally_01.mp4`
- Match: Jannik Sinner vs Novak Djokovic, 2025 Wimbledon semifinal
- Source: official Wimbledon YouTube channel
- URL: https://www.youtube.com/watch?v=eoiKSfYg71o
- Source interval: 00:44–01:07
- Clip duration: 23.0 seconds
- Resolution and frame rate: 1280×720, 25 FPS

## Rights and redistribution status

The source, uploader, and URL are documented, but no explicit reusable licence
has been verified for either video. The complete source videos and benchmark
clips are therefore kept local and are not committed or redistributed.

The main README includes one short, silent, modified GIF derived from the test
source solely to demonstrate the system's overlays. It identifies the match,
tournament, official channel, and original URL, does not claim a free licence,
and is not part of the benchmark data.

## Evaluation status

The development clip contains 39 annotated in-play racket-ball contacts. A
later contact by Sinner after the point had already ended is intentionally not
part of the ground truth. The test clip contains 15 annotated in-play contacts,
for a total of 54 scored events.

Development and test data are separated by source video. The test split must
not be used for parameter tuning. These annotations are frozen before running
the baseline and must not be moved merely to improve evaluation results.

## Annotation protocol

- Include serves and all racket-ball contacts while the point is in play.
- Exclude contacts after the point has ended.
- Record the closest visible contact frame using the source video's FPS.
- Store `frame` and `time_seconds` in one CSV file per clip.
- Treat this as a small benchmark, not as evidence of broad model performance.

Predicted events will be matched one-to-one with ground-truth events within
±0.25 seconds. Evaluation will report precision, recall, F1, false positives,
false negatives, and mean absolute timing error for matched events.

## Frozen development baseline

The baseline uses the existing five-frame rolling mean and fixed 25-frame
direction-change persistence rule. It was evaluated before changing any shot
detection parameters.

- Ball model: `models/yolov11best.pt`
- Ball model SHA-256: `1f74aea3f7e84ccfbf61d0633d3f0d9713b20f2a7709771b8f9afa426a315d8c`
- Development video SHA-256: `ef8c2e3adf02b956e9312706eaddb0b471b5a011847c13024b9f6a64a2d8f8a0`
- Predictions: `predictions/development_australian_open_2024_sinner_medvedev_baseline.csv`

| Metric | Development result |
| --- | ---: |
| Ground-truth events | 39 |
| Predicted events | 33 |
| True positives | 27 |
| False positives | 6 |
| False negatives | 12 |
| Precision | 0.8182 |
| Recall | 0.6923 |
| F1 | 0.7500 |
| Mean absolute timing error | 0.0563 s |

The baseline test result was calculated only after the improved configuration
had been selected on the development split. It was used for the final
comparison, not for parameter selection.

## Development-selected improvement

Error analysis showed that 10 of the 12 baseline false negatives had a nearby
direction change rejected by the fixed 25-frame persistence requirement. A
development-only sweep varied that requirement while keeping the model,
detections, interpolation, smoothing, annotations, and evaluator unchanged.

Thresholds 17–19 tied for the best development F1. The midpoint, 18 frames,
was selected as the final candidate.

| Metric | Baseline (25 frames) | Selected candidate (18 frames) |
| --- | ---: | ---: |
| Ground-truth events | 39 | 39 |
| Predicted events | 33 | 43 |
| True positives | 27 | 34 |
| False positives | 6 | 9 |
| False negatives | 12 | 5 |
| Precision | 0.8182 | 0.7907 |
| Recall | 0.6923 | 0.8718 |
| F1 | 0.7500 | 0.8293 |
| Mean absolute timing error | 0.0563 s | 0.0612 s |

This is a measured development trade-off: recall and F1 rise, but precision and
timing accuracy decrease slightly on this single development video.

## Frozen test result

The 18-frame candidate was evaluated once on the Wimbledon test clip after the
parameter was frozen. The 25-frame baseline was then calculated from the same
cached model detections for a like-for-like comparison. No parameter was
changed after seeing these results.

- Test video SHA-256: `fe847658c21da9fb5bae8ede5b11d369a82e5bd1ca97149ef84580399190ee10`
- Baseline predictions: `predictions/test_wimbledon_2025_sinner_djokovic_baseline.csv`
- Selected predictions: `predictions/test_wimbledon_2025_sinner_djokovic_persistence_18.csv`

| Metric | Baseline (25 frames) | Selected candidate (18 frames) |
| --- | ---: | ---: |
| Ground-truth events | 15 | 15 |
| Predicted events | 16 | 17 |
| True positives | 9 | 11 |
| False positives | 7 | 6 |
| False negatives | 6 | 4 |
| Precision | 0.5625 | 0.6471 |
| Recall | 0.6000 | 0.7333 |
| F1 | 0.5806 | 0.6875 |
| Mean absolute timing error | 0.0578 s | 0.0509 s |

The selected candidate improves every reported test metric on this clip. This
supports the development-set decision, but the benchmark is deliberately small
and does not establish performance across tournaments, camera angles, or video
qualities.

## v0.6 frame-rate normalization

The frozen v0.5 benchmark used 25 FPS video and selected an 18-frame
persistence threshold with a five-frame rolling mean. In v0.6 these values are
represented by their equivalent durations: 0.72 seconds of persistence and
0.20 seconds of smoothing.

For each video, the detector converts both durations using the source FPS. The
smoothing window is kept odd to prevent a symmetric direction change from
passing through an exact zero between positive and negative deltas. The
historical 25-frame baseline is represented as 1.0 second at 25 FPS.

The conversion reproduces all four frozen development and test prediction
files byte for byte at 25 FPS. The reported v0.5 metrics and CSV files are
unchanged. Tests with equivalent synthetic trajectories at 25, 30, and 60 FPS
verify consistent event times, but this is not presented as a new benchmark
result.

Example persistence options for the local benchmark runner:

```bash
# Historical baseline at 25 FPS
python -m benchmark.run_baseline \
  --video path/to/clip.mp4 \
  --output predictions.csv \
  --persistence-seconds 1.0

# Development-selected v0.5 configuration, normalized for source FPS
python -m benchmark.run_baseline \
  --video path/to/clip.mp4 \
  --output predictions.csv \
  --persistence-seconds 0.72
```

## Multi-clip evaluation with confidence intervals

`benchmark/sources.csv` lists every clip and its split. The runner evaluates
one or more methods on all clips and reports block-bootstrap confidence
intervals. With two or more methods, the second is compared to the first with a
paired bootstrap on the same resampled blocks.

```bash
python -m benchmark.run_benchmark --methods baseline persistence_18
python -m benchmark.run_benchmark --methods baseline persistence_18 --splits test
```

Predictions are read from `benchmark/predictions/<clip>_<method>.csv`; for the
historical files the `_rally_NN` part of the clip name may be omitted.

Events within a rally are correlated, so each clip is split into 10-second
blocks (`--block-seconds`) and whole blocks are resampled with replacement. A
true positive or false negative belongs to the block of its ground-truth time, a
false positive to the block of its prediction time. `--block-seconds 0`
resamples whole clips, which is only meaningful with many clips: with two clips
it produces misleadingly narrow intervals.

Current two-clip result (both clips now classified as development data, so the
interval is optimistic for the tuned method):

| Method | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| baseline | 0.735 [0.540, 0.886] | 0.667 [0.544, 0.772] | 0.699 [0.545, 0.822] |
| persistence_18 | 0.750 [0.596, 0.883] | 0.833 [0.705, 0.939] | 0.790 [0.649, 0.906] |

Paired difference (persistence_18 − baseline): recall +0.167 [+0.122, +0.241],
F1 +0.090 [+0.027, +0.149], precision +0.015 [−0.082, +0.091]. The recall gain is
consistent across blocks; precision is unchanged. The fresh test split will
provide the unbiased confirmation.

## Ball detections as data

Experiments on the shot-detection rule only need the model's raw per-frame ball
boxes, not the videos. `benchmark/detections/<clip>.csv` stores them
(`frame,x1,y1,x2,y2`, empty when the ball was not detected) and contains only
box coordinates. Export them once, on the machine that holds the local detection
caches:

```bash
ls -lt tracker_stubs/ball_detections_*.pkl
python -m benchmark.detections export \
  --cache tracker_stubs/ball_detections_<hash>.pkl \
  --output benchmark/detections/<clip>.csv
```

The command prints the frame count and detection rate, which identifies the clip
(the development clip has 1,300 frames, the Wimbledon clip 575).
