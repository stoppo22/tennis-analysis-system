# Experiment: retrain the ball detector (architecture, size, data)

This protocol was committed **before** any model was trained or evaluated for it.

## Motivation

The published ball model (`models/yolov11best.pt`, YOLO11l) was fine-tuned on 578 images
and has a recall of 0.475 on its own validation set. The benchmark showed that the ball
is the weakest link: it is detected in fewer than half of the test frames, and running
the same weights at 960 px instead of 640 px already improves the shot events found
(see `EXPERIMENT_input_resolution.md`). Two things can still be improved at the
source: the data the model learns from, and the architecture and size.

This experiment asks both questions on a larger, labelled dataset, without any new
manual annotation of the ball.

## Data

**TrackNet tennis dataset** (Kaggle copy `sofuskonglevoll/tracknet-tennis`): 10 broadcast
videos at 1280x720 and 30 fps, 95 rally clips, 19,842 frames in total, with the ball
position in every frame. The labels are a point per frame (x, y), a visibility class
(0 not in the image, 1 easily identified, 2 hard to identify, 3 occluded) and a
trajectory pattern. When the ball is blurred the label is the **latest position of the
trace**, so it can be a few pixels off the centre of the blur.

| Game | Match | Surface |
| ---: | --- | --- |
| 1 | Federer v Djokovic, Shanghai 2014 | hard |
| 2 | Djokovic v Monfils, Eastbourne 2017 | grass |
| 3 | Murray v Djokovic, Doha 2017 | hard |
| 4 | ITF Future 2014 | clay |
| 5 | Checa v Rumenov | hard |
| 6 | Ferrer v Fognini, Buenos Aires 2014 | clay |
| 7 | Federer v Kyrgios, Laver Cup 2017 | black court |
| 8 | Sharapova v Vinci, 2017 | clay |
| 9 | Sharapova v Halep, US Open 2017 | hard |
| 10 | Universiade 2017 final | hard |

**Licence.** The dataset's terms are not stated in the copies found and the official
page could not be reached. It is described as intended for educational use. The data are
used here for research and evaluation, they are not redistributed, and **the trained
weights are kept local** and are not published as a release asset unless the licence is
clarified.

**Split by video, not by frame** (consecutive frames are almost identical, so a frame
split would leak):

- train: games 1, 2, 4, 5, 7, 10;
- validation (selection of the model size): games 3 and 8;
- test (ball-level comparison, used once for the chosen model): games 6 and 9.

Each split has at least one clay video.

**Training images.** Every 4th frame with visibility class 1 is a positive example. Every
4th frame with class 0 (ball outside the image) is a negative example with no box.
Classes 2 and 3 are left out of training because it is not clear that a ball is visible.
The point label becomes a square box centred on it. The side is fixed once, by looking at
a sample of 50 frames before any training, and is recorded in the results. The
dataset conversion is a script of this repository so it can be reproduced.

## Models and recipe

All arms use the Ultralytics version pinned in `requirements.txt` (8.4.123), start
from the COCO-pretrained checkpoint of their family, and share one recipe: image size
960, batch 8, 30 epochs, seed 0, `deterministic=True`, automatic mixed precision, the
default augmentations. The 960 px size is chosen because it was the better input size at
inference; the images are 1280 px wide, so the ball keeps three quarters of its native
size.

| Arm | Model |
| --- | --- |
| reference | published `yolov11best.pt`, **not retrained**, run at 960 |
| control | YOLO11l, retrained with the recipe above |
| candidates | YOLO26n, 26s, 26m, 26l, 26x |

A short pilot (one epoch of the smallest and of the largest model) checks time and
memory on the Kaggle GPU. If a model cannot finish within one session, the epochs and
the batch size are reduced **for all arms alike** and the change is recorded before any
result is read. Nothing else changes between arms.

## Metrics

**Ball level** (new, uses the TrackNet labels): for every frame the most confident
detection at confidence 0.15 is kept. A frame of class 1 counts as found if the
detection centre is within 1.25% of the frame width of the label (16 px at 1280). Reported:

- recall: share of class 1 frames that are found;
- false-detection rate: share of class 0 frames with any detection;
- precision: share of frames with a detection where the detection is correct, class 1
  and class 0 frames together;
- F1 of the last two quantities with recall.

Intervals: block bootstrap over clips (10,000 resamples, seed 0).

**Shot events** (the project's real target): `swing_v1` and `persistence_18` with the
static filter, on the four development clips (35 contacts), as in the other experiments.
These clips are 1080p and come from other matches than TrackNet.

## Decision rules (fixed now)

1. **Choice of size.** On the validation games, among the candidates, the chosen
   model is the **smallest** whose ball-level F1 is within 0.02 of the best candidate.
   The size order is n, s, m, l, x. The value 0.02 is a margin for the difference between
   two training runs; it is checked afterwards by repeating the control with seeds 1
   and 2, and if its spread is larger than 0.02 the margin is raised to that spread and
   the choice is redone and reported as such.
2. **Is the chosen model better than the published one?** On the test games, the chosen
   model, the control and the reference are compared once. The chosen model is proposed
   if its ball-level F1 exceeds the reference by at least 0.05 with the paired
   bootstrap interval above zero.
3. **Does it help the shot events?** On the development clips, the proposed model must
   have a pooled F1 not lower than the reference at 960 px (point estimates, for both
   `swing_v1` and `persistence_18`). If not, the new model is reported as better at
   finding the ball but not adopted.

If rule 2 is not met, the experiment is reported as negative and the published model
stays. The architecture comparison (control against candidates) is reported either way.

## Not part of this experiment

Extra training images made from our own match footage (self-labelling), higher input
sizes, and the P2 variants of YOLO26 are separate experiments, each with its own
protocol, decided after these results. The test split of the shot-event benchmark is
not used.

## What would and would not be claimed

A positive outcome would say that, on TrackNet videos not used for training and on four
development clips, the retrained model finds the ball better than the published one. It
would not establish an improvement on the shot events of other matches; that is left to
the final confirmation on fresh matches. TrackNet labels have their own convention (the
latest position of the trace) and its videos are 720p from 2014-2017, so ball-level
scores are not comparable with those of other benchmarks.

---

# Amendments

## Amendment 1: epochs and memory (after the pilot, before any result of the sweep)

A pilot ran one epoch of YOLO26n and YOLO26x on the Kaggle GPU (T4, image size 960, batch
8) to measure time and memory. It showed, per epoch including validation:

| Model | Time per epoch | Peak GPU memory |
| --- | ---: | ---: |
| YOLO26n | 125 s | 2.8 GB |
| YOLO26x | 644 s | 15.05 GB |

Extrapolating to the other sizes, 30 epochs for six models would need about 19 GPU hours,
too many for the weekly quota once the repetitions with other seeds are added. As foreseen
above, the recipe is reduced **for every arm alike**:

- epochs: 30 -> **20** (about 7,100 iterations of batch 8 on 2,855 training images, more
  iterations than the 100 epochs of batch 16 on 578 images used for the published model);
- batch size stays 8 and the image size stays 960.

The validation scores of the pilot (one epoch) were looked at but they carry no
information on the final quality, and played no part in this change.

YOLO26x used 15.05 GB, practically all the memory of the T4. If it fails with an out of
memory error in the sweep, it is reported as not fitting a 16 GB GPU with this recipe and
is left out of the selection, without changing the recipe for it.

The sweep is run in two sessions of about six hours each: YOLO26n, s, m and the YOLO11l
control first, then YOLO26l and YOLO26x.

---

# Results of sweep session 1 (YOLO26 n, s, m and the YOLO11l control)

Run on a Kaggle T4, commit `808e0b3`, 20 epochs, image size 960, batch 8, seed 0, trained
on the 2,855 training images and scored on the **validation** games only (3 and 8:
801 frames with a visible ball, 78 without). The test games were not used. Reports are in
`benchmark/results/ball_sweep1/`; training curves and arguments in its `training_curves/`.
One run per arm, so the spread between runs is not yet measured (rule 1 requires the
control repeated with seeds 1 and 2).

| Model | Parameters | Precision | Recall | **F1** | Frames without ball with a detection | Training time | Peak GPU memory |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| reference (published YOLO11l, not retrained) | 25.3 M | 0.896 | 0.657 | 0.758 [0.709, 0.801] | 4 of 78 | - | - |
| control (YOLO11l retrained) | 25.3 M | 0.808 | 0.734 | 0.769 [0.706, 0.824] | 23 of 78 | 99 min | 12.1 GB |
| YOLO26n | 2.5 M | 0.885 | 0.833 | **0.858** [0.811, 0.897] | 25 of 78 | 27 min | 2.8 GB |
| YOLO26s | 9.9 M | 0.850 | 0.823 | 0.836 [0.772, 0.886] | 41 of 78 | 45 min | 5.4 GB |
| YOLO26m | 21.8 M | 0.759 | 0.725 | 0.742 [0.650, 0.822] | 26 of 78 | 88 min | 10.5 GB |

The F1 intervals are 10,000 block-bootstrap resamples (5 s blocks). Inference per image
on the same T4: 0.022 s (n), 0.029 s (s), 0.050 s (m), 0.057 s (control).

## Reading

- The smallest model has the highest validation F1, and the F1 falls as the model grows
  (n 0.858, s 0.836, m 0.742). The intervals of n and s overlap, and so do those of s and
  m. A likely reason is that the larger models fit the 2,855 training images (six videos)
  more closely in 20 epochs and generalise less to new videos, but this was not tested.
- YOLO26n and YOLO26s are above the reference and the control; YOLO26m and the control
  are within the noise of the reference.
- The retrained models fire on many more frames in which the ball is not in the image
  (23-41 of 78, against 4 of 78 for the reference). These are only 78 frames and the
  detection may be a different ball or a mark, but it is a cost to check on the shot
  events, where false detections matter.
- Rule 1 is **not applied yet**: YOLO26l and YOLO26x (session 2) are still to come, and
  the margin has to be measured with the repeated control.

## Exploratory look at the shot events (not the decision of rule 3)

Before session 2, YOLO26n (best epoch weights) was run once on the four development clips
(35 contacts) exactly as in the input-resolution experiment: image size 960, confidence
0.15, last box of the frame, static-detection filter, 10 s blocks, 10,000 resamples. The
test split was not touched. Compared with the published model at 960 px:

| Method | Published, 960 px | YOLO26n, 960 px | Paired difference |
| --- | ---: | ---: | ---: |
| `swing_v1` | 0.698 | 0.781 | +0.083 [-0.055, +0.219] |
| `persistence_18` | 0.684 | 0.812 | +0.128 [+0.010, +0.231] |

YOLO26n finds a detection in 1,087 of the 1,288 frames (84%), against 66.9% for the
published model. Both point estimates are positive. This is a preview made with the
session-1 winner before the sweep is complete; rule 3 will be applied to the model chosen
by rule 1. Files: `benchmark/detections_yolo26n_imgsz960/`, the `*_yolo26n.csv` files in
`benchmark/predictions/`, and `dev_shot_events_*` in `benchmark/results/ball_sweep1/`.

# Results of sweep session 2 (YOLO26 l and x)

Run on a Kaggle T4, commit `387a666`, same recipe as session 1 (20 epochs, image size 960,
batch 8, seed 0), validation games only. Reports in `benchmark/results/ball_sweep2/`.
YOLO26x fitted in memory (15.08 GB peak), so no model is left out of the selection.

| Model | Parameters | Precision | Recall | **F1** | Frames without ball with a detection | Training time | Peak GPU memory |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| YOLO26l | 26.2 M | 0.737 | 0.738 | 0.737 [0.657, 0.805] | 53 of 78 | 113 min | 12.7 GB |
| YOLO26x | 58.8 M | 0.840 | 0.774 | 0.806 [0.749, 0.853] | 21 of 78 | 206 min | 15.1 GB |

Inference per image on the T4: 0.061 s (l), 0.105 s (x).

## Rule 1 on the five sizes (single seed, margin not yet measured)

| Size | n | s | m | l | x |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation F1 | **0.858** | 0.836 | 0.742 | 0.737 | 0.806 |

The best candidate is YOLO26n (0.858), and it is also the smallest size, so **rule 1 picks
YOLO26n whatever the margin is**: a larger margin could only favour a smaller model, and
there is none. The F1 does not grow with the size: it falls from n to l and rises again at
x, and all the intervals overlap. The picture is of five models close to each other, with
the smallest one nominally ahead, on one seed. The repeats below still measure the spread
between runs, which says how much weight the choice can bear, as rule 1 requires.

# Results of the repeats (YOLO26n and the control, seeds 1 and 2)

Run on a Kaggle T4, commit `71e16fc`, same recipe, validation games only. Reports in
`benchmark/results/ball_repeats/` (seed 0 is in `ball_sweep1/`).

| Model | Seed | Precision | Recall | F1 | Frames without ball with a detection |
| --- | ---: | ---: | ---: | ---: | ---: |
| YOLO26n | 0 | 0.885 | 0.833 | 0.858 [0.811, 0.897] | 25 of 78 |
| YOLO26n | 1 | 0.959 | 0.811 | 0.879 [0.843, 0.908] | 11 of 78 |
| YOLO26n | 2 | 0.857 | 0.838 | 0.847 [0.794, 0.891] | 46 of 78 |
| control YOLO11l | 0 | 0.808 | 0.734 | 0.769 [0.706, 0.824] | 23 of 78 |
| control YOLO11l | 1 | 0.814 | 0.737 | 0.773 [0.704, 0.833] | 18 of 78 |
| control YOLO11l | 2 | 0.864 | 0.684 | 0.764 [0.703, 0.815] | 17 of 78 |

- Spread of the control: range 0.010 (standard deviation 0.005), below 0.02, so **the margin
  of rule 1 stays at 0.02**. Rule 1 still picks YOLO26n.
- YOLO26n: mean F1 0.861 over three seeds, range 0.032 (standard deviation 0.016). The
  spread is larger than the control's but all three seeds are above 0.84, well above every
  control run (mean 0.769) and above the reference (0.758). The F1 of YOLO26n is therefore
  not a lucky seed.
- The detections on frames without a ball vary a lot between seeds of YOLO26n (11, 25 and
  46 of 78) while F1 hardly moves, so this number is not stable enough to be read as a
  property of the model.

**Model used for rules 2 and 3.** Fixed here, before any test game is scored: the YOLO26n
weights of **seed 0**, the original sweep run (the one already used in the exploratory look
at the shot events). It is not chosen among the seeds by score. The seeds 1 and 2 are
reported as the spread.

## Status and next steps

1. Sessions 1, 2 and the repeats are done. Rule 1 is applied: YOLO26n, margin 0.02.
2. Evaluate YOLO26n (seed 0), the control (seed 0) and the reference **once** on the test
   games (rule 2), then the shot events on the development clips (rule 3).
3. Trained weights are kept locally and not released, because the licence of the TrackNet
   data is not stated.
