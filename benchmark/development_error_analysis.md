# Development baseline error analysis

This analysis was performed using only the Australian Open development clip.
At the time of analysis, the Wimbledon test split had not been run or inspected
through model predictions.

## Baseline summary

- Ground-truth events: 39
- Predicted events: 33
- True positives: 27
- False positives: 6
- False negatives: 12
- Precision: 0.8182
- Recall: 0.6923
- F1: 0.7500
- Mean absolute timing error: 0.0563 seconds

The raw ball model produced a detection in 600 of 1,300 frames (46.2%). Missing
positions were interpolated before applying the existing shot-event rule.

## False-negative findings

For 10 of the 12 false negatives, a vertical direction change exists near the
annotated contact but fails the fixed requirement of 25 consistent following
frames. Several candidates reach 22, 23, or 24 frames and are narrowly rejected.

The other two false negatives have accepted predictions shifted by 7 and 8
frames (0.28 and 0.32 seconds), just outside the 0.25-second matching tolerance.
Both occur near sparse raw ball detections.

## False-positive findings

Five of the six false positives are within 0.60 seconds of a ground-truth
event. They appear more consistent with shifted or duplicate direction changes
than with unrelated events. The remaining false positive is 1.16 seconds from
the nearest ground-truth event.

## Evidence-based experiment

Only the direction-change persistence threshold was varied on the development
set. The ball model, cached detections, interpolation, smoothing, matching, and
annotations remained fixed. This directly tested the dominant observed failure
mode without introducing a new smoothing or direction model.

| Persistence frames | Predictions | TP | FP | FN | Precision | Recall | F1 | Mean timing error |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 15 | 44 | 34 | 10 | 5 | 0.7727 | 0.8718 | 0.8193 | 0.0612 s |
| 16 | 44 | 34 | 10 | 5 | 0.7727 | 0.8718 | 0.8193 | 0.0612 s |
| 17 | 43 | 34 | 9 | 5 | 0.7907 | 0.8718 | 0.8293 | 0.0612 s |
| 18 | 43 | 34 | 9 | 5 | 0.7907 | 0.8718 | 0.8293 | 0.0612 s |
| 19 | 43 | 34 | 9 | 5 | 0.7907 | 0.8718 | 0.8293 | 0.0612 s |
| 20 | 40 | 32 | 8 | 7 | 0.8000 | 0.8205 | 0.8101 | 0.0625 s |
| 21 | 38 | 30 | 8 | 9 | 0.7895 | 0.7692 | 0.7792 | 0.0667 s |
| 22 | 35 | 29 | 6 | 10 | 0.8286 | 0.7436 | 0.7838 | 0.0662 s |
| 23 | 33 | 27 | 6 | 12 | 0.8182 | 0.6923 | 0.7500 | 0.0667 s |
| 24 | 33 | 27 | 6 | 12 | 0.8182 | 0.6923 | 0.7500 | 0.0667 s |
| 25 (baseline) | 33 | 27 | 6 | 12 | 0.8182 | 0.6923 | 0.7500 | 0.0563 s |

Thresholds 17, 18, and 19 produced identical event metrics. The midpoint, 18,
was selected rather than an edge of that plateau. Compared with the frozen
baseline, it adds seven true positives and removes seven false negatives, at
the cost of three additional false positives. F1 increases from 0.7500 to
0.8293, while mean timing error increases from 0.0563 to 0.0612 seconds.

The selected development predictions are stored in
`predictions/development_australian_open_2024_sinner_medvedev_persistence_18.csv`.
After this choice was frozen, the selected configuration was evaluated once on
the test split. No parameter was changed from the test result; the final numbers
are reported in `README.md`.
