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

---

# Results

All numbers below are reproducible with the stored detections
(`benchmark/detections/`) and the result files in `benchmark/results/`:

| File | Content |
| --- | --- |
| `swing_vs_persistence_preregistered.json` | Pre-registered LOCO run (39 configurations) |
| `swing_vs_persistence_extended_grid.json` | Exploratory LOCO run with a wider swing grid (98 configurations) |
| `persistence_18_vs_swing_v1_in_sample.json` | Frozen configuration vs. `persistence_18` on both clips (in-sample) |

Commands:

```bash
python -m benchmark.loco_experiment --json benchmark/results/swing_vs_persistence_preregistered.json
python -m benchmark.loco_experiment --extended-grid --json benchmark/results/swing_vs_persistence_extended_grid.json
python -m benchmark.run_benchmark --methods persistence_18 swing_v1
```

## 1. Pre-registered result (leave-one-clip-out)

Each clip is scored with the configuration selected on the other clip. Pooled
over both held-out clips (54 events):

| Method | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| `persistence` (re-tuned per fold) | 0.738 [0.579, 0.873] | 0.833 [0.702, 0.943] | 0.783 [0.639, 0.899] |
| `swing` | 0.807 [0.683, 0.912] | 0.852 [0.736, 0.946] | 0.829 [0.713, 0.920] |

Paired difference, `swing` minus `persistence` (95% block bootstrap):

| Metric | Difference |
| --- | ---: |
| Precision | **+0.069 [+0.007, +0.142]** |
| Recall | +0.019 [−0.070, +0.122] |
| F1 | +0.046 [−0.020, +0.120] |

P(swing F1 > persistence F1) = 0.905.

**Verdict against the pre-registered criterion: inconclusive.** The F1 interval
includes zero, so the criterion ("interval positive") was not met. The precision
gain is the only metric whose interval excludes zero.

## 2. Deviation from the protocol: the optimum was at the grid edge

On both folds the pre-registered search selected the largest ratio (0.26) and
the largest smoothing (0.28 s) in the grid, so the optimum could lie outside it.
This was **not** foreseen in the protocol. A follow-up with a wider grid (ratio up
to 0.50, smoothing up to 0.52 s; 91 swing + 7 persistence configurations in total)
was therefore run and is labelled **exploratory**. It is not part of the
pre-registered result and the number of configurations examined is stated above.

| Method (exploratory grid) | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| `swing` | 0.833 [0.718, 0.930] | 0.833 [0.720, 0.933] | 0.833 [0.720, 0.928] |

Paired difference vs. `persistence`: precision **+0.096 [+0.028, +0.180]**, recall
+0.000 [−0.071, +0.075], F1 +0.051 [−0.013, +0.128]. The conclusion is the same
as in the pre-registered run: higher precision at equal recall, F1 not
distinguishable from zero with two clips.

## 3. Parameter sensitivity: a broad plateau

Pooled F1 over the exploratory grid (rows: swing ratio, columns: smoothing in
seconds):

| ratio \ smoothing | 0.08 | 0.12 | 0.20 | 0.28 | 0.36 | 0.44 | 0.52 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.06 | 0.662 | 0.662 | 0.698 | 0.803 | 0.800 | 0.814 | 0.814 |
| 0.12 | 0.693 | 0.693 | 0.765 | 0.800 | 0.814 | 0.814 | 0.829 |
| 0.22 | 0.765 | 0.765 | 0.779 | 0.829 | 0.829 | 0.829 | 0.829 |
| 0.30 | 0.772 | 0.772 | 0.800 | 0.836 | 0.836 | 0.836 | 0.836 |
| 0.40 | 0.786 | 0.786 | 0.800 | 0.836 | 0.836 | 0.836 | 0.836 |
| 0.50 | 0.793 | 0.793 | 0.800 | 0.836 | 0.833 | 0.833 | 0.833 |

- Smoothing is the dominant parameter: below 0.20 s F1 falls to 0.66–0.79; at
  0.28 s and above it is stable.
- Once smoothing is at least 0.28 s and the ratio at least 0.22, F1 barely
  changes. In the exploratory grid, 63 of 91 swing configurations (69%) are
  within 0.05 F1 of the best on **both** clips, against 3 of 7 (43%) for the
  persistence rule. The swing detector is therefore less sensitive to its
  hyper-parameters, which matters when no large tuning set is available.
- On the Wimbledon clip, F1 reaches the same ceiling (0.759) across most of the
  plateau, so its remaining errors are not parameter-limited.

## 4. Frozen configuration (`swing_v1`)

To avoid picking a point by eye, the rule fixed here is: take the centre of the
region where pooled F1 is within 0.005 of the maximum (0.836). That region spans
ratio 0.30–0.50 and smoothing 0.28–0.52 s; its centre gives
**`min_swing_ratio = 0.40`, `smoothing_seconds = 0.36`**. These are the defaults in
`utils/swing_shot_detection.py` and are not to be changed before the fresh test
split is evaluated.

These values were chosen using both clips, so the following in-sample numbers
are **descriptive, not evidence of generalization**:

| Clip | Method | Precision | Recall | F1 | Mean timing error |
| --- | --- | ---: | ---: | ---: | ---: |
| Australian Open (39 events) | baseline | 0.818 | 0.692 | 0.750 | 0.0563 s |
| | `persistence_18` | 0.791 | 0.872 | 0.829 | 0.0612 s |
| | `swing_v1` | 0.833 | 0.897 | 0.864 | 0.1006 s |
| Wimbledon (15 events) | baseline | 0.562 | 0.600 | 0.581 | 0.0578 s |
| | `persistence_18` | 0.647 | 0.733 | 0.688 | 0.0509 s |
| | `swing_v1` | 0.786 | 0.733 | 0.759 | 0.0982 s |

Pooled, `swing_v1` minus `persistence_18`: precision +0.071 [+0.008, +0.147],
recall +0.019 [−0.071, +0.119], F1 +0.047 [−0.019, +0.122] (P(better) = 0.903).

## 5. Timing error roughly doubles

The mean absolute timing error of matched events rises from about 0.05–0.06 s
to about 0.10 s. The 0.36 s smoothing that stabilises the detector also moves
each extremum away from the true contact frame, because hits are sharp
reversals while the smoothed curve is rounded. At a ±0.25 s tolerance this
costs little in F1, but it makes `swing_v1` less suitable where the exact
contact frame matters (for example speed estimates between consecutive hits).
This is the main trade-off of the method and is not resolved here.

## 6. Remaining errors (post-hoc inspection, no further tuning)

With `swing_v1` the Australian Open clip has 7 false positives and 4 false
negatives; the Wimbledon clip 3 and 4.

- **Most errors are shifted rather than invented events.** Of the 10 false
  positives, 9 lie within 0.28–0.84 s of an annotated event, and 7 of the 8
  misses (FN) have a false positive nearby (for example false positives at
  8.96, 10.16 and 11.84 s around the misses at 9.32, 10.76 and 12.12 s). A
  shift just beyond the ±0.25 s tolerance counts as one FP plus one FN.
- **They cluster where the ball is poorly detected.** The Australian Open
  segment around 10.76 s has an observation ratio of 0.08 in the surrounding
  25 frames, so the trajectory there is mostly interpolated.
- **The first serve is missed on Wimbledon (0.92 s).** The ZigZag filter does not
  emit the first and last samples, and the ball toss precedes the contact.
- Together with the 62% / 46% raw ball detection rates, this points to the ball
  detector, not the event rule, as the next bottleneck.

## 7. Conclusion and limits

- Under a protocol where both methods are tuned identically, the alternating-swing
  detector gives **higher precision at equal recall** (+0.07 to +0.10, interval
  excluding zero), and is **markedly less sensitive to its parameters**.
- The F1 gain (+0.05) is **not statistically established** with two clips.
- Timing accuracy is **worse** (about 0.10 s versus 0.05–0.06 s).
- All evidence is from two 25 FPS broadcast clips featuring the same player and
  both are development data. 98 configurations were examined in total, plus one
  untuned sanity run, so some optimism is expected even in the LOCO figures.
- **No generalization claim is made.** Confirmation requires the fresh test
  split (`CLIP_SELECTION.md`), evaluated once with `swing_v1` frozen.

## 8. Next steps

1. Evaluate `swing_v1` and `persistence_18` once on the fresh test split.
2. Recover timing accuracy, for example by moving each pivot to the strongest
   local reversal in a lightly smoothed signal within the pivot's neighbourhood.
   This must be specified as a pre-registered variant, not tuned on the
   current clips.
3. Add player proximity (needs the player-detection cache and court keypoints
   exported like the ball detections) to reject shifted and duplicate events.
4. Improve ball detection recall, the likely dominant error source.

---

# Confirmation on the held-out test split

The development evidence above was inconclusive for F1 (+0.046 [-0.020, +0.120]) and
the configuration `swing_v1` was frozen (ratio 0.40, smoothing 0.36 s) before the test
clips existed. The test split was then built as described in `CLIP_SELECTION.md`
(Amendments 2-5): random windows from four full matches, visual triage, annotation
by hand, frozen annotations, and only afterwards the ball model run over the 28
clips (`benchmark.export_model_detections`, confidence 0.15, image size 640, last box
of the frame, as in the pipeline) and the methods applied
(`benchmark.predict_from_detections`). The evaluation was run **once**:

```bash
python -m benchmark.run_benchmark --methods persistence_18 swing_v1 baseline \
  --splits test --json benchmark/results/test_evaluation.json
```

No parameter, clip, annotation or threshold was changed after seeing the result.

## Result (208 contacts, 28 clips, 4 matches)

| Method | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| `baseline` (1.0 s) | 0.489 [0.374, 0.594] | 0.317 [0.236, 0.402] | 0.385 [0.293, 0.471] |
| `persistence_18` | 0.458 [0.363, 0.548] | 0.466 [0.376, 0.555] | 0.462 [0.375, 0.544] |
| `swing_v1` | 0.587 [0.500, 0.670] | 0.567 [0.484, 0.649] | 0.577 [0.499, 0.651] |

`swing_v1` minus `persistence_18`: precision +0.130 [+0.058, +0.201], recall +0.101
[+0.046, +0.160], F1 +0.115 [+0.063, +0.168]; P(better) = 1.000. By the criterion fixed
in advance (F1 interval above zero with no large precision loss) the confirmation
**succeeded**.

## Consistency across matches

F1 per match (counts pooled over the clips of a match):

| Match | Clips | Contacts | `baseline` | `persistence_18` | `swing_v1` |
| --- | ---: | ---: | ---: | ---: | ---: |
| Roland-Garros 2025 final (clay, 50 FPS) | 9 | 78 | 0.224 | 0.337 | 0.533 |
| US Open 2026 final (hard, 59.94 FPS) | 7 | 39 | 0.594 | 0.675 | 0.686 |
| Nitto ATP Finals 2023 (indoor, 25 FPS) | 6 | 53 | 0.405 | 0.526 | 0.592 |
| Wimbledon 2026 (grass, 25 FPS) | 6 | 38 | 0.457 | 0.447 | 0.556 |

`swing_v1` has the highest F1 in every match, but the margin over `persistence_18`
varies from +0.011 (US Open) to +0.196 (Roland-Garros). It has a higher F1 than
`persistence_18` on 21 of 28 clips, lower on 5 and equal on 2. These breakdowns are
descriptive; they were computed after the single evaluation and were not used to
change anything.

## Timing

Mean absolute timing error of matched events over the whole split: 0.071 s
(`baseline`), 0.077 s (`persistence_18`), 0.117 s (`swing_v1`). The trade-off seen on
development data (smoothing rounds the extrema) is confirmed: `swing_v1` detects more
events correctly but places them less precisely.

## Ball detection on the test clips

The ball model produced a detection in 47.5% of the 15,760 test frames: 66.4% in
Roland-Garros, 33.6% in Wimbledon, 27.9% in the ATP Finals and 27.7% in the US Open
(development clips: 46% and 62%). Missing positions are interpolated before event
detection, so every method is limited by this. This study did not test why detection
is lower in three matches (candidates are image size, broadcast, lighting and the
small training set); the model card lists these as known limitations.

## What is and is not claimed

- Claimed: on this test split, `swing_v1` finds more of the annotated contacts and
  raises fewer false alarms than the persistence rule applied to the same ball
  detections, with intervals that exclude zero.
- Not claimed: that F1 0.58 is good in absolute terms, that the result holds for other
  broadcasts, camera heights or sports, that the gain survives a better ball
  detector, or that `swing_v1` is better where timing matters.
- Caveats: annotations are from a single person in a first pass; four matches give
  clustered data and two of them share a player; clips were chosen by one visual
  review; the bootstrap treats 10-second blocks as exchangeable. The second
  annotation pass will bound the annotation noise.
