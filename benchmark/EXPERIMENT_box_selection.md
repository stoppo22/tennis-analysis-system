# Experiment: keep the most confident box instead of the last one

This protocol was committed **before** any result of this experiment was computed.

## Motivation

When the ball model reports several candidate boxes in a frame, the pipeline keeps the
**last** one in the result (`BallTracker.detect_frame`). The boxes of a result come out
of non-maximum suppression, normally ordered by confidence, so the last box would
usually be the least confident candidate. If that holds, the pipeline throws away the
best candidate whenever there are several. This is a reading of the code and of the
library's usual behaviour; it has not been checked on these clips, and the experiment
below does not depend on it being true.

## Question

Does keeping the most confident box (`--selection confidence` in
`benchmark.export_model_detections`) improve shot-event detection compared with keeping
the last one (`--selection last`), for `swing_v1` and `persistence_18`, when the
static-detection filter is already applied in both arms?

## Data

The four development clips whose video is available on the machine that runs the
model (two Australian Open 2025 clips and two Rome 2025 clips, 1080p), 35 annotated
contacts. The two original development clips cannot be re-run because their videos are
not available, so they are left out of this comparison. This is a small sample and the
result will have wide intervals. The test split is **not** used.

Same model, confidence threshold 0.15, image size 640. Events are scored as in the
other experiments (one-to-one, +-0.25 s, block bootstrap with 10 s blocks, 10,000
resamples, seed 0), with a paired bootstrap on the same blocks.

## Decision rule (fixed now)

Keeping the most confident box becomes the proposed default if, on these four clips and
with the static filter applied in both arms, the point estimate of the pooled F1
difference (confidence minus last) is **at least zero for both `swing_v1` and
`persistence_18`**. With 35 contacts the interval cannot be expected to exclude zero,
so no condition is placed on it; the decision is a reasoned choice supported by weak
evidence, and the confirmation is deferred to a fresh test on new matches that will cover
all improvements together.

If the rule is not met, the experiment is reported as negative and the default stays
`last`.

## Label-free diagnostics (reported, not used for the decision)

For both arms: share of frames with a detection, share of consecutive detected frames
with a jump of more than one frame width per second, and the number of frames in which
more than one candidate box exists is not recorded by the export tool and is therefore
not reported.

## What would and would not be claimed

A positive outcome would say that, on four clips, the most confident box gave an
equal or better F1 than the last one. It would not establish a general improvement.

---

# Results

Four development clips, 35 contacts, static-detection filter applied in both arms.

| Method | F1, last box | F1, most confident box | Paired difference |
| --- | ---: | ---: | ---: |
| `swing_v1` | 0.625 [0.491, 0.746] | 0.645 [0.415, 0.817] | +0.020 [-0.107, +0.114] |
| `persistence_18` | 0.537 [0.273, 0.711] | 0.559 [0.295, 0.763] | +0.022 [-0.057, +0.088] |

Precision and recall move by a few hundredths in both directions; none of the
differences is distinguishable from zero.

## Decision rule

The point estimate of the F1 difference is above zero for both methods (+0.020 and
+0.022), so by the rule fixed in advance keeping the most confident box becomes the
**proposed** default. This is a formal outcome of the rule, not evidence of an
improvement: the effect is of the size of the noise, with intervals of about +-0.1.

## Label-free diagnostics (before the static filter)

- The two rules choose a **different box in 32.7%** of the frames in which both have a
  detection (229 of 700), so the choice is not irrelevant.
- The share of detected frames is the same in both arms (54.3%).
- Consecutive detected frames jumping by more than one frame width per second: 17.9%
  with the last box and 20.3% with the most confident one (586 pairs). This goes in the
  opposite direction to the F1 point estimates, and it is measured before the static
  filter, which removes a fixed mark that may be the most confident candidate.

## Reading

The experiment cannot say whether the most confident box is better. The sample is
small, the effect is within noise, and the plausibility diagnostic does not support it.
The assumption in the motivation, that the last box is usually the least confident, was
not checked directly. The default of the pipeline therefore stays the last box, and the
most confident one is carried into the final confirmation on new matches as an explicit
option to be compared there, together with the other improvements.
