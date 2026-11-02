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
