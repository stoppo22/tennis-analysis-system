# Experiment: run the ball model at a higher input resolution

This protocol was committed **before** any result of this experiment was computed.

## Motivation

The ball model is run with an image size of 640 pixels. A 1080p broadcast frame
(1920 px wide) is therefore scaled down by a factor of three before detection, and the
ball, already only a few pixels across, shrinks further. The ball detector is the first
link of the chain, and the label-free audit of the test clips showed that the ball is
detected in fewer than half of the frames (47.5%, and only 28-34% outside the Roland
Garros clips). Running the **same weights** on a larger image is the cheapest possible
change: it needs no training, no GPU and no new annotation.

There is a reason it may not help: the model was trained on images at 640, so a ball
that is larger than in the training images may be recognised less well, and a larger
input also produces more false candidates (court marks, shoes, logos).

## Question

Does running the published ball model at an image size of 960 or 1280, instead of 640,
improve shot-event detection for `swing_v1` and `persistence_18`, when the
static-detection filter is applied in every arm?

## Data

The four development clips whose video is available on the machine that runs the model
(two Australian Open 2025 and two Rome 2025 clips, 1080p), 35 annotated contacts. As in
the box-selection experiment this is a small sample, and the intervals will be wide.
The test split is **not** used.

## Arms

All arms use the same weights (`models/yolov11best.pt`), confidence threshold 0.15 and
`--selection last`, the behaviour of the pipeline; only `--imgsz` changes.

| Arm | `--imgsz` |
| --- | ---: |
| control | 640 |
| medium | 960 |
| large | 1280 |

The control arm is re-run in the same environment as the others, so that the three arms
differ only in image size. As a sanity check its detections are compared with the stored
ones in `benchmark/detections/`.

Events are scored as in the other experiments (one-to-one, +-0.25 s, block bootstrap
with 10 s blocks, 10,000 resamples, seed 0), with a paired bootstrap on the same blocks.
The static-detection filter is applied to every arm before the shot detectors run.

## Decision rule (fixed now)

An image size becomes a **proposed** option for the final confirmation on new matches if,
compared with the control arm, the point estimate of the pooled F1 difference is **at
least +0.03 for both `swing_v1` and `persistence_18`**. If both 960 and 1280 satisfy the
rule, the smaller one is proposed, because the cost grows with the image area. With 35
contacts the intervals are expected to include zero, so no condition is placed on them;
as before, the rule yields a reasoned choice backed by weak evidence, and the real
confirmation is deferred to fresh matches.

If neither size satisfies the rule, the experiment is reported as negative and the
pipeline keeps 640.

Two sizes are compared with the control, so the rule has two chances to be satisfied by
chance; this is stated here rather than corrected for, and it is one more reason the
outcome is only a proposal.

## Label-free diagnostics (reported, not used for the decision)

For every arm: share of frames with a detection, number of detections removed by the
static filter, share of consecutive detected frames with a jump of more than one frame
width per second, and the inference time per frame on the machine used (Apple silicon,
MPS or CPU, stated in the results).

## What would and would not be claimed

A positive outcome would say that, on four clips, a larger input gave a better F1 with
the same weights. It would not establish a general improvement, and it would not say
that the model is optimal at that size: a model trained at the larger size could behave
differently, and that is a separate experiment that needs a GPU.

---

# Results

Four development clips, 35 contacts, same weights, confidence 0.15, last box,
static-detection filter applied in every arm. The 640 arm reproduces the stored
detections in `benchmark/detections/` byte for byte, so its files are not duplicated.
Machine: Apple silicon, MPS.

| Method | F1 at 640 | F1 at 960 | F1 at 1280 |
| --- | ---: | ---: | ---: |
| `swing_v1` | 0.625 [0.491, 0.746] | 0.698 [0.593, 0.778] | 0.535 [0.313, 0.711] |
| `persistence_18` | 0.537 [0.273, 0.711] | 0.684 [0.556, 0.769] | 0.455 [0.255, 0.640] |

Paired differences against 640:

| Method | 960 minus 640 | 1280 minus 640 |
| --- | ---: | ---: |
| `swing_v1` | +0.073 [-0.060, +0.186] | -0.090 [-0.293, +0.087] |
| `persistence_18` | +0.146 [+0.051, +0.292] | -0.083 [-0.285, +0.191] |

At 960 `persistence_18` gains mostly recall (+0.257 [+0.100, +0.419]) and `swing_v1`
gains precision (+0.096) and recall (+0.057), but only the `persistence_18` F1 interval
excludes zero.

## Decision rule

At 960 both point estimates (+0.073 and +0.146) are above +0.03, so **960 becomes the
proposed image size**. At 1280 both are negative, so it does not qualify, and the
smaller size would have been chosen anyway.

## Label-free diagnostics (before the static filter)

| Image size | Frames with a detection | Consecutive pairs jumping more than a frame width per second | Time per frame |
| ---: | ---: | ---: | ---: |
| 640 | 54.3% (700 of 1,288) | 17.9% (105 of 586) | 0.12 s |
| 960 | 66.9% (862) | 15.8% (119 of 754) | 0.25 s |
| 1280 | 78.4% (1,010) | 22.6% (211 of 935) | 0.48 s |

Times are the wall-clock time of the whole export (video decoding included) divided by
the number of frames.

Detections increase steadily with the image size, but not all of the extra ones are the
ball: at 1280 the jump rate rises and the number of detections the static filter must
remove grows (193 in the Rome w2 clip against 58 at 640), and both precision and recall
fall. At 960 the extra detections come with a lower jump rate, which is consistent with
more real ball positions rather than more spurious ones.

## Reading

On these four clips a larger input helps up to a point: 960 is better than 640 for both
detectors, 1280 is worse. The size of the effect at 960 is large for `persistence_18`
and moderate for `swing_v1`, but the sample is small (35 contacts, four clips from two
matches) and two sizes were compared with the control, so one of them could pass by
chance. The result is therefore a **proposal**. The pipeline
default stays 640 until 960 is checked on new matches together with the other changes
(`swing`, `--suppress-static`, box selection).

Inference at 960 is about twice as slow as at 640.
