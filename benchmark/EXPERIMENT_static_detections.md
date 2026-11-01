# Experiment: suppressing static ball detections

This protocol was committed **before** the development evaluation was computed. The
only information used beforehand is label-free: the audit below, which looks at the
detections alone, and a visual look at three detection crops.

## Motivation (label-free audit of the ball detections)

After the held-out test evaluation of the shot detectors, the ball model was found to
detect the ball in 47.5% of the test frames, but the rate does not track the event
F1 of the matches: Roland-Garros has the highest rate (66.4%) and the lowest F1
(`swing_v1` 0.533), the US Open the lowest rate (27.7%) and the highest F1 (0.686).

Looking only at where detections fall, in 6 of the 9 Roland-Garros test clips a single
16-pixel cell holds between 22% and 63% of all detections (w2_rally_07: 63%,
w4_rally_03: 61%, w4_rally_05: 46%, w2_rally_05: 35%, w6_rally_01: 30%, w6_rally_03:
22%). In the Roland-Garros clips 16.1% of consecutive detected frames jump by more than
one frame width per second, against 3-9% in the other matches, and the median
detection moves almost not at all. Three of these positions were enlarged and
inspected by eye: the box lies on a smudge of the clay (a bounce mark), with no ball in
it. The inspection is three samples and shows the cause; it does not measure how often
it happens.

## Rule

`tennis_analysis.utils.detection_filters.suppress_static_detections`: a detection is
removed if at least `ceil(1.0 s x fps)` detections of the same clip, itself included,
have their centre within `1.2%` of the frame width of its own centre (about 23 px at
1920 px). A real ball cannot stay inside that radius for a second, except at rest on the
ground. The two constants were fixed from this reasoning and from the frame sizes, and
are **not tuned** on any clip. Removed detections become gaps, which the existing
interpolation fills.

## Question

Does removing static detections improve shot-event detection for `swing_v1` and
`persistence_18` on the development clips?

## Development data and metrics

The six development clips with a hand annotation: the two original clips (720p, 25
FPS; they are the clips on which `persistence_18` was selected, which does not matter
here because the filter has no parameters fitted on them) and the four 1080p clips of
the second sampling (two Australian Open 2025, two Rome 2025 on clay), 89 contacts in
total. Detections come from the same ball model, confidence 0.15, image size 640, last
box of the frame. Events are scored as in the other experiments (one-to-one matching,
+-0.25 s, block bootstrap with 10 s blocks, 10,000 resamples, seed 0). The comparison is
with and without the filter, per method, with a paired bootstrap on the same blocks.

## Decision rule (fixed now)

The filter goes to the confirmation step if, on the development clips, **the point
estimate of the pooled F1 difference (with minus without the filter) is at least zero
for both `swing_v1` and `persistence_18`, and the lower bound of the 95% interval for
`swing_v1` is above -0.05**. Otherwise it is reported as a negative result on
development data and is not run on the test split.

## Confirmation

If the rule is met, the filter is applied **once** to the test split, with the same
methods and parameters, and the paired difference is reported whatever it is. The test
split was already evaluated once for the shot detectors, so this is a **second use** of
it and the interval is not independent of the earlier result. It is reported as such.

## What would and would not be claimed

A positive confirmation would support the statement that removing static detections
raises event F1 for this ball model on these broadcasts. It would not show that the
ball model itself is better, nor that the result holds on other surfaces, broadcasts or
detectors, nor would it say how many of the removed detections were wrong, since the
ball has not been annotated.

---

# Results

## Development (decision step)

Six development clips, 89 contacts. Static detections removed: 0 in the two original
clips and in Australian Open w2_rally_05, 176 in Australian Open w3_rally_05, 58 in
Rome w2_rally_01 and 168 in Rome w3_rally_03.

| Method | F1 without | F1 with | Paired difference |
| --- | ---: | ---: | ---: |
| `swing_v1` | 0.698 [0.554, 0.821] | 0.759 [0.656, 0.849] | +0.060 [+0.000, +0.151] |
| `persistence_18` | 0.621 [0.450, 0.763] | 0.696 [0.552, 0.812] | +0.075 [+0.014, +0.165] |

The decision rule was met (point estimates above zero for both methods, lower bound
for `swing_v1` above -0.05), so the filter went to the confirmation step.

## Confirmation on the test split (second use of the test)

28 clips, 208 contacts, 4 matches, same ball detections and methods. Static
detections removed: Roland-Garros 2,289 (9 clips), ATP Finals 259 (6), US Open 213
(7), Wimbledon 179 (6). The filter was applied once.

| Method | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| `swing_v1` | 0.587 [0.500, 0.670] | 0.567 [0.484, 0.649] | 0.577 [0.499, 0.651] |
| `swing_v1` with filter | 0.668 [0.590, 0.743] | 0.649 [0.570, 0.723] | 0.659 [0.586, 0.724] |
| `persistence_18` | 0.458 [0.363, 0.548] | 0.466 [0.376, 0.555] | 0.462 [0.375, 0.544] |
| `persistence_18` with filter | 0.586 [0.502, 0.660] | 0.591 [0.516, 0.664] | 0.589 [0.516, 0.655] |

Paired differences (with minus without filter): `swing_v1` F1 **+0.082 [+0.020,
+0.150]** (precision +0.081 [+0.018, +0.150], recall +0.082 [+0.011, +0.158]);
`persistence_18` F1 **+0.127 [+0.061, +0.202]** (precision +0.128, recall +0.125). The
intervals exclude zero for both methods.

The filter helps the weaker method more, so the gap between the two shrinks: with the
filter, `swing_v1` has F1 0.659 and `persistence_18` 0.589 (point estimates; the paired
interval of this gap was not part of the protocol and was not computed). The earlier
conclusion that `swing_v1` beats `persistence_18` is not weakened by the filter, but
a smaller part of that difference now comes from the rule and a larger part had come
from how each rule copes with false detections.

## What is and is not claimed

- Claimed: removing detections that stay in one place for about a second raises event
  F1 for both rules on both development and test clips, with the test interval
  excluding zero.
- The interval of the test confirmation is **not independent** of the earlier test
  evaluation: the same clips and annotations were used twice, although no parameter
  was tuned on them.
- Not shown: how many of the removed detections were wrong (the ball has not been
  annotated; three enlarged samples showed marks on the clay), whether a real ball is
  ever removed, or that the result holds for other ball models, surfaces or
  broadcasts.
- Roland-Garros contributes most of the removed detections (2,289 of 2,940); the other
  three matches changed much less.
