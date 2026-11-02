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
