# Experiment: remove detections that need an impossible ball speed

This protocol was committed **before** any result of this experiment was computed.

## Motivation

The label-free diagnostics of the input-resolution experiment show that a share of the
consecutive detections is far apart: 15-23% of the consecutive pairs move more than one
frame width per second. Part of that is genuine fast play, but part is the model
reporting something that is not the ball (a shoe, a logo, a line judge) for a frame or
two, away from the rest of the trajectory. Such a detection can create a false direction
change, and therefore a false shot event. A physical limit on the speed allows removing
the isolated ones without any label.

## The filter

`suppress_implausible_jumps` (`tennis_analysis/utils/detection_filters.py`): a detection
is removed if it has the previous and/or next detection within 0.4 s and none of them
can be reached at a speed of at most **3.0 frame widths per second**. A detection with
no neighbour in range is kept, and so are two adjacent false detections that agree with
each other (a known limitation).

Both parameters are fixed here from physical reasoning, not from F1. At the baseline of
a broadcast shot, a frame width spans roughly 22 m, so 3 frame widths per second is about
66 m/s, or 240 km/h, faster than a record serve; a real ball does not exceed it. The
speed distribution of the consecutive detections of the four development clips was
looked at (no labels used): the median is 0.3 frame widths per second, the 90th
percentile about 1.0, and 5% of the pairs exceed 3.0. The expected effect is therefore
small.

## Question

Does applying the filter after the static-detection filter improve shot-event detection
for `swing_v1` and `persistence_18`?

## Data and arms

The four development clips with an available video (35 contacts), using the detections
of the proposed image size, 960 px (`benchmark/detections_imgsz960`). The test split is
**not** used.

- control: static filter only (the `_nostatic_imgsz960` predictions of the previous
  experiment);
- candidate: static filter, then jump filter (`--suppress-jumps`).

As a secondary check, the same comparison is run on the 640 px detections
(`benchmark/detections`). The secondary check does not enter the decision.

Events are scored as in the other experiments (one-to-one, +-0.25 s, block bootstrap
with 10 s blocks, 10,000 resamples, seed 0), with a paired bootstrap on the same blocks.

## Decision rule (fixed now)

The filter becomes a **proposed** option for the final confirmation if, on the 960 px
detections, the point estimate of the pooled F1 difference (candidate minus control) is
**at least +0.01 for both `swing_v1` and `persistence_18`**. With 35 contacts and an
expected small effect no condition is placed on the intervals. If the rule is not met,
the experiment is reported as negative and the filter is not used.

## Label-free diagnostics (reported, not used for the decision)

Number of detections removed per clip, and the share of consecutive detected pairs
moving faster than one frame width per second before and after the filter.

## What would and would not be claimed

A positive outcome would say that, on four clips, removing impossible jumps did not hurt
and slightly helped. It would not establish an improvement, and with only a handful of
detections expected to be removed it may well show no difference at all, which is also a
valid result.

---

# Results

Four development clips, 35 contacts, static filter applied in both arms.

| Image size | Method | F1 without the jump filter | F1 with the jump filter | Paired difference |
| ---: | --- | ---: | ---: | ---: |
| 960 | `swing_v1` | 0.698 | 0.698 | +0.000 [+0.000, +0.000] |
| 960 | `persistence_18` | 0.684 | 0.701 | +0.018 [+0.000, +0.041] |
| 640 (secondary) | `swing_v1` | 0.625 | 0.625 | +0.000 [+0.000, +0.000] |
| 640 (secondary) | `persistence_18` | 0.537 | 0.571 | +0.034 [+0.000, +0.142] |

## Decision rule

The rule required a difference of at least +0.01 for **both** methods at 960 px. For
`swing_v1` it is exactly zero, so the rule is **not met**. The experiment is negative
for the proposed use: the jump filter is not added to the pipeline and is not carried
into the final confirmation.

## Label-free diagnostics

The filter removes very few detections: 12 at 960 px (9 of them in one Australian Open
clip) and 4 at 640 px. Consecutive pairs moving faster than one frame width per second
go from 10.6% to 6.1% at 960 px and from 7.6% to 5.0% at 640 px (these shares are
measured after the static filter, so they are lower than the 15-23% before it in the
input-resolution experiment).

## Reading

The filter does what it is designed to do, removing isolated impossible positions, but
there are too few of them to change what `swing_v1` finds: its smoothed swing signal
already ignores a single stray detection. `persistence_18` gains one or two events
(two fewer false positives at 960 px, two more true positives at 640 px), consistent
with a small real effect for the simpler detector, but that is not the detector in use.
With 35 contacts a difference of a few events cannot be distinguished from noise. The
function stays in `detection_filters.py` and in `benchmark.predict_from_detections`
(`--suppress-jumps`) so that the result can be reproduced; the pipeline is unchanged.
