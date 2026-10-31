# Experiment: alternating-swing shot detector

This protocol was committed **before** the grid was evaluated. The only result
seen beforehand is one untuned sanity run of the swing detector at
`ratio=0.10, smoothing=0.12 s` (development: 33 TP / 20 FP / 6 FN; Wimbledon:
11 TP / 11 FP / 4 FN), used only to check that the implementation works.

## Question

Does detecting alternating swings of the ball's vertical position
(`utils/swing_shot_detection.py`) beat the direction-persistence rule
(`utils/shot_detection_utils.py`) when **both methods are tuned under the same
protocol**?

## Why the comparison needs care

`persistence_18` was selected on the development clip, so comparing a new method
against it on that clip favours the old method, while tuning the new method on
the same data favours the new one. With only two clips, any reported gain must
come from **leave-one-clip-out (LOCO)** evaluation: parameters are chosen on the
other clips and scored on the held-out clip.

## Methods and grids (fixed in advance)

| Method | Parameters | Grid |
| --- | --- | --- |
| `persistence` (existing rule) | persistence seconds, smoothing fixed at 0.20 s | 0.52, 0.60, 0.68, 0.72, 0.80, 0.88, 1.00 (7 configs) |
| `swing` (new) | swing ratio × smoothing seconds | ratio 0.06, 0.08, 0.10, 0.12, 0.15, 0.18, 0.22, 0.26 × smoothing 0.08, 0.12, 0.20, 0.28 (32 configs) |

Total configurations evaluated: **39**. Interpolation, matching tolerance
(±0.25 s) and annotations are unchanged.

## Selection and scoring rules

- **Selection:** on the training clips, pool event counts and pick the
  configuration with the highest F1. Ties are broken by the larger first
  parameter (more conservative), then the larger second parameter.
- **Scoring:** each clip is scored with the configuration chosen without it.
  Held-out counts are pooled and reported with 95% block-bootstrap intervals.
- **Comparison:** `swing` minus `persistence`, paired bootstrap on the same
  blocks of the held-out predictions.
- **Also reported, not used for claims:** the in-sample best per clip (oracle)
  and the fraction of each grid within 0.05 F1 of its best on every clip, as a
  measure of how sensitive each method is to its parameters.

## What would count as success

A paired F1 difference whose interval is positive under LOCO, with no large
loss in precision. Anything else is reported as inconclusive. Because both clips
are development data, even a positive result is **development evidence**; the
confirming evaluation is the fresh test split described in
`CLIP_SELECTION.md`, run once with the parameters frozen.
