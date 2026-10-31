# Evaluation methodology

This document describes how shot-event detection is evaluated in this project and
why each design choice was made. Commands and results are in
[`benchmark/README.md`](../benchmark/README.md) and
[`benchmark/EXPERIMENT_swing_detector.md`](../benchmark/EXPERIMENT_swing_detector.md).

## Task

Given a rally video, a detector returns the instants at which a player hits the
ball. Ground truth is the set of instants a human marked while stepping through
the clip frame by frame (`benchmark/annotate_shots.py`): every racket-ball contact
while the point is in play, including serves, and none after the point has ended.

## Matching and metrics

A predicted event is a **true positive** if it lies within a tolerance of an
unmatched ground-truth event; the default tolerance is ±0.25 s. Matching is
**one-to-one** and maximises, in order, the number of matches and then the
smallest total timing error. This prevents a cluster of duplicate predictions
from being credited against a single true event.

- **Precision** = TP / (TP + FP): how many detections are real.
- **Recall** = TP / (TP + FN): how many real events are found.
- **F1** = 2·TP / (2·TP + FP + FN): the harmonic mean of the two.
- **Mean absolute timing error** over matched events, reported separately because
  F1 at a ±0.25 s tolerance can hide a systematic delay.

A prediction displaced by slightly more than the tolerance counts as one false
positive and one false negative, so F1 is sensitive to the tolerance. The
tolerance is fixed before evaluation and is not tuned.

## Uncertainty: block bootstrap

With tens of events a single F1 value is not informative without an interval.
Events within a rally are correlated, so resampling individual events would give
intervals that are too narrow. Each clip is therefore split into 10-second blocks
and **whole blocks are resampled with replacement** (10,000 resamples, fixed
seed). A true positive or false negative belongs to the block of its
ground-truth time, a false positive to the block of its prediction time. Reported
intervals are 95% percentile intervals.

To compare two methods, both are scored on the **same resampled blocks**
(paired bootstrap). The interval of the metric difference then reflects the
improvement itself, not the uncertainty of each method separately. A difference is
treated as established only if its interval excludes zero.

## Avoiding optimistic estimates

1. **Split by source match.** Development and test data never share a match, since
   rallies from one match are not independent.
2. **A test set is used once.** After a clip has been scored it is development
   data. The original Wimbledon test clip was reclassified for this reason.
3. **Equal treatment of compared methods.** A new method is compared with a
   baseline tuned under the same protocol, not with a baseline tuned elsewhere.
4. **Leave-one-clip-out selection** when only a few clips exist: parameters are
   chosen on the other clips and scored on the held-out one.
5. **Pre-registration.** The methods, parameter grids, selection rule and success
   criterion are committed before the results exist, so the Git history shows that
   they were not adjusted afterwards. Deviations are recorded in the same document,
   labelled exploratory, and the number of configurations examined is stated.
6. **Frozen configuration.** The configuration to be confirmed is chosen by a rule
   fixed in advance and not changed before the confirming evaluation.

## Annotation quality

Ground truth contains human error. Each test clip is annotated twice on different
days, and `benchmark/compare_annotations.py` reports the agreement between the two
passes (F1 at the same tolerance, timing differences, systematic bias). That
agreement is a practical ceiling: a detector that scores close to it is limited by
the annotations rather than by the method.

## Known limitations

- Few clips, few matches, and few players; results describe those conditions only.
- Confidence intervals assume that blocks are exchangeable, which is approximate.
- The ±0.25 s tolerance is a convention; other tolerances give different F1.
- Ball positions come from a detector with limited recall, so event detection and
  ball detection errors are not separated by this benchmark.
