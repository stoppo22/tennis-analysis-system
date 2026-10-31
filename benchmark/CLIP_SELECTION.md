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

Cover as many of these axes as possible across the new clips. Clips from the
same match always belong to the same split.

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
- 8–60 seconds long, containing one complete point (see the amendment below).
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

## Finding and preparing clips

### Where to look

Full-match uploads on the official tournament channels are the best source:
long rallies are shown from the standard high camera without cuts. Extended
highlights are poor sources because they are edited. Search each channel for
`<tournament> <year> full match` and pick a point of at least six shots that is
shown without a cut or replay. Availability varies by region and over time, and
the video must be inspected before use; nothing in this repository links to a
specific third-party upload.

### Coverage plan

Six or more matches, with up to six rallies from each (see the amendment below).
Cover as many rows as possible.

| Slot | Split | Surface | Draw | Notes |
| --- | --- | --- | --- | --- |
| 1 | test | Clay | Men | Roland Garros channel |
| 2 | test | Hard | Women | US Open channel |
| 3 | test | Grass | Women | Wimbledon channel, not the existing match |
| 4 | test | Indoor hard | Men | ATP or tournament channel |
| 5 | test | Hard, 50 or 60 FPS | Men | Check FPS with `check_clip` |
| 6 | test | Clay | Women | Different tournament from slot 1 |
| 7 | development | Hard | Women | Australian Open channel |
| 8 | development | Clay or hard | Men | Include a left-handed player |
| 9 | development | Any | Any | Different broadcaster or camera height |

The table fixes the split of each slot **before** a clip is chosen. A clip that
fails the checks is replaced by another one for the same slot, not moved to a
different split.

### Cutting a clip

Download the video with a tool you are permitted to use, then cut the interval
without changing the frame rate (no `-r` option) and without audio:

```bash
ffmpeg -ss 00:44 -to 01:07 -i source.mp4 -an \
  -c:v libx264 -crf 18 -preset slow \
  input_videos/benchmark/<split>_<tournament>_<year>_<playerA>_<playerB>_rally_01.mp4
```

Keep source downloads and clips under `input_videos/`, which Git ignores.

### Automatic checks

```bash
python -m benchmark.check_clip input_videos/benchmark/<clip>.mp4
```

The checker verifies resolution, duration, absence of shot changes and camera
steadiness, computes the SHA-256, and prints a `sources.csv` row. It does **not**
replace a visual check of the court, the players, singles play, and the absence
of replays or slow motion.

**Camera check is advisory.** The camera-drift threshold was validated only on
synthetic video and on a six-second demo excerpt (17.8 px against a limit of about
22 px), so a warning does not reject a clip; look at it by eye. After the first
five or six accepted clips, compare the measured drift of clips that look steady
with those that visibly pan or zoom, and set `MAX_CAMERA_DRIFT_FRACTION` (and
remove the advisory flag) from that evidence.

### Annotation

Annotate every accepted clip with `python -m benchmark.annotate_shots`. For the
test split, annotate each clip a second time on a different day and keep both
files, so that inter-annotation agreement can be measured. Only after all test
annotations are frozen and committed may any detector be run on those clips.

## Amendment 1: one clip per rally, several rallies per match

*Made before any new clip was inspected, annotated or run through a detector.*

The original requirement of 20–60 s without a cut cannot be met by a full-match
broadcast: the director cuts to close-ups between points and most rallies last
under 15 s. The protocol is therefore changed as follows.

- A benchmark clip is **one uninterrupted rally of 8–60 s** from the standard
  camera. Up to six rallies may be taken from the same match, named
  `..._rally_01`, `..._rally_02`, and so on.
- All clips from a match share its split. Because rallies of one match are not
  independent, the test split must contain **at least four different matches**,
  and the bootstrap blocks are the 10 s blocks of each clip, so intervals should
  be read with this clustering in mind.
- The sample-size target is unchanged: at least 100 scored events in the test
  split.
- `benchmark/find_rallies.py` lists the uninterrupted segments of a full match
  with thumbnails and `ffmpeg` commands; `benchmark/check_clip.py` then verifies
  each exported clip.

```bash
python -m benchmark.find_rallies input_videos/benchmark/raw/<match>.mp4 \
  --thumbnails input_videos/benchmark/candidates/<match>
```

Replays and slow motion are also uninterrupted segments and cannot be detected
reliably; every candidate must be checked by eye (the thumbnails help), including
for a scoreboard or graphic that shows the replay is not live.

### Match assignment (fixed before extraction)

`candidate_matches.csv` lists the full matches supplied by the project author and
the split assigned to each. Test matches cover one surface each; development gets
the rest. The identities (players, year) are recorded by the author because they
could not be verified automatically.

## Amendment 2: random windows instead of whole matches

*Made before any new clip was inspected, annotated or run through a detector.*

Full matches can last several hours, so only short random windows are downloaded.

1. Get the real duration without downloading: `yt-dlp --print duration "<url>"`.
2. `python -m benchmark.sample_windows <match_id> <duration_seconds> --url "<url>"`
   prints three non-overlapping windows of 150 s and the matching `yt-dlp`
   commands. Positions come from a seed derived from the match id, so anyone can
   regenerate them. The first 10% and the last 5% of the video are excluded
   (introductions, warm-up, trophy ceremony).
3. Download the windows, run `find_rallies` on each, and keep **every**
   uninterrupted live rally of at least 8 s, in chronological order, up to six per
   match. Do not choose rallies by how clean they look. A window with no usable
   rally is recorded as such in `candidate_matches.csv`.
4. Reject a rally only for an objective reason: replay or slow motion, a graphic
   covering the court, the court not fully visible, or a doubles match.

Clips are named `<split>_<match_id>_w<k>_rally_<NN>.mp4`.

Four test matches with three windows each give about a dozen windows; with one or
two usable rallies per window this is expected to reach the 100-event target for
the test split, but this is an estimate and is checked after annotation.
