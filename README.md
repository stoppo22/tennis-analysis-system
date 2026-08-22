# Tennis Analysis System

Computer-vision project that analyses tennis videos with Python, OpenCV,
PyTorch, and YOLO. The pipeline detects players and the ball, estimates court
keypoints, maps movement onto a mini court, identifies shot events, calculates
speed statistics, and produces an annotated video.

## Project status: v0.6

The project now includes a small, video-separated benchmark for tennis-shot
detection and a measured improvement over the original rule:

| Split | Baseline F1 | Improved F1 |
| --- | ---: | ---: |
| Development | 0.7500 | 0.8293 |
| Test | 0.5806 | 0.6875 |

The improvement was selected using only the development video and then
evaluated once on the test video. Event evaluation uses one-to-one matching
within ±0.25 seconds and reports precision, recall, F1, false positives, false
negatives, and mean absolute timing error.

In v0.6, the shot detector's persistence and smoothing thresholds are expressed
as durations instead of fixed frame counts. They are converted using each
video's FPS, while preserving the frozen v0.5 behavior exactly at 25 FPS. This
is a frame-rate normalization change, not a new F1 improvement claim.

See the [benchmark documentation](benchmark/README.md) for the annotation
protocol, source information, complete metrics, error analysis, and known
limitations.

## Project origin

The initial pipeline was built by following a YouTube tutorial. The current
work extends that starting point through pipeline validation, safer detection
caching, automated tests, a reproducible evaluation workflow, manual benchmark
annotations, development-set error analysis, and a quantitatively tested shot
detection improvement. The shot-event thresholds have also been normalized for
different video frame rates.

## Current limitations

- The benchmark contains only two short clips and 54 annotated in-play shots.
- Its results do not establish performance across tournaments, camera angles,
  or video qualities.
- Both benchmark clips are 25 FPS; cross-FPS behavior is covered by controlled
  trajectory tests and a local 30 FPS smoke test, not a multi-FPS benchmark.
- The benchmark videos are kept local and are not redistributed because an
  explicit reusable licence has not been verified.
- Model weights, input videos, generated outputs, and detection caches are not
  stored in Git.

## Next milestone

Before v1.0, the repository history must be cleaned of old binary artifacts.
The final milestone will also add complete setup and asset instructions, a
short demo, final verification, and a CV-ready project description.
