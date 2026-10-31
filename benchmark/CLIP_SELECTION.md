# Benchmark expansion: clip selection protocol

The current benchmark has two clips and 54 events, which is too small for
reliable conclusions (the held-out gain is two true positives). This protocol
defines how to extend it to a benchmark that supports confidence intervals and
meaningful ablations.

## Split policy

- The existing Wimbledon clip was scored once as a test clip. It has been seen,
  so **it is now treated as development data**. Further tuning on it would
  otherwise bias any new claim.
- New clips are assigned to a split **before** any model or detector is run on
  them, and the assignment is recorded in `sources.csv`.
- Split by **source video / match**, never by rally within the same match.
- The new test split is frozen and not run until every method to compare is
  fixed. It is evaluated once per method.

| Split | Contents | Use |
| --- | --- | --- |
| `development` | Two existing clips + 4 new clips | Error analysis, tuning, ablations |
| `test` | 4–6 new clips (never run during development) | Final, one-shot evaluation |

Target: at least **200 scored events** in the new test split combined with
development, and at least **100 events in the test split alone** so that a
bootstrap confidence interval is informative.

## What to look for

Cover as many of these axes as possible across the new clips. No two test clips
should share the same match.

| Axis | Target variety |
| --- | --- |
| Surface | Hard, clay, grass, indoor hard |
| Tournament / broadcaster | At least 4 different channels or tournaments |
| Players | Women's and men's, left- and right-handed, not only Sinner |
| Frame rate | 25, 30, and 50 or 60 FPS (the pipeline normalizes by FPS, but this has not been benchmarked) |
| Resolution | 720p and 1080p |
| Rally length | Mix of short points (serve + return) and long rallies |
| Lighting | Day, evening, roof closed |

## Hard requirements for each clip

- **Single continuous shot** from the standard high camera behind a baseline.
  The court keypoints are estimated on the first frame only, so cuts, replays,
  and slow motion break the pipeline. Pick clips that do not include them.
- Whole court visible at the start of the clip, with both players on court.
- Singles only.
- 20–60 seconds long, containing one or more complete points.
- No scoreboard or graphics covering the ball path for long stretches.
- Original frame rate preserved; do not convert or re-encode with changed FPS.

## Sources and rights

Use footage you are allowed to use locally for research, for example official
tournament highlights channels. For every clip:

- Record the exact URL, channel, match, tournament, and time interval in
  `sources.csv`.
- Keep clips **local** under `input_videos/benchmark/` (ignored by Git). Do not
  commit or redistribute them; only annotations, predictions, and the manifest
  are tracked.
- Compute and record the SHA-256 of each clip so that results are tied to the
  exact file.

```bash
shasum -a 256 input_videos/benchmark/<clip>.mp4
```

## Naming convention

```text
<split>_<tournament>_<year>_<playerA>_<playerB>_rally_<NN>.mp4
```

Example: `test_roland_garros_2025_alcaraz_sinner_rally_01.mp4`.

Annotations go to `benchmark/annotations/<same name>.csv` and are created with
`python -m benchmark.annotate_shots`.

## Annotation protocol (unchanged)

- Include serves and every racket-ball contact while the point is in play.
- Exclude contacts after the point has ended.
- Record the closest visible contact frame at the source FPS.
- Annotations are frozen before any detector is run on the clip. Do not move
  them to improve results.
- Recommended: annotate each test clip twice on different days and measure the
  disagreement (inter-annotation agreement). This quantifies the noise ceiling
  of the ±0.25 s matching.

## Checklist per clip

- [ ] Split assigned and recorded in `sources.csv`
- [ ] Source, URL, interval, FPS, resolution recorded
- [ ] Clip is a single shot, court visible, no replays
- [ ] SHA-256 recorded
- [ ] Annotated and CSV committed
- [ ] (Test clips) not run through any detector until methods are frozen
