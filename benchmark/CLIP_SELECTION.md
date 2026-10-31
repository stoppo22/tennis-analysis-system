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

The checker verifies resolution and duration and the absence of shot changes,
computes the SHA-256, and prints a `sources.csv` row. It does **not** replace a
visual check of the court, the players, singles play, the camera angle, and the
absence of replays or slow motion.

**Camera steadiness is not checked automatically.** An automatic drift measure was
tried and removed as a criterion: on 26 clips judged steady by eye it measured
65-168 px (at 1920 px wide), and on five candidates rejected for camera movement
103-171 px, so it does not separate the two. It is still printed, labelled
informational. See Amendment 3 for how steadiness was judged.

### Annotation

Annotate every accepted clip with `python -m benchmark.annotate_shots`. For the
test split, annotate each clip a second time on a different day and keep both
files, so that inter-annotation agreement can be measured. Only after all test
annotations are frozen and committed may any detector be run on those clips.

### Inter-annotation agreement

Store the second pass in a separate directory (for example
`benchmark/annotations_second_pass/`, same file names) and compare:

```bash
python -m benchmark.compare_annotations \
  --first benchmark/annotations --second benchmark/annotations_second_pass
```

The pooled agreement F1 is the practical ceiling for any detector scored against
these annotations, and the signed timing difference shows whether one pass is
systematically earlier or later. See `docs/evaluation-methodology.md`.

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

### Matches registered (metadata read from the video pages)

`candidate_matches.csv` holds the title, channel, duration and upload date of each
match as reported by the video page; players, tournament and year follow from
those titles. Splits were assigned before the windows were downloaded and
therefore before any footage was inspected. Two points to keep in mind:

- Carlos Alcaraz appears in three of the six matches (two in the test split, one
  in development) and Jannik Sinner in the Roland-Garros final and in both
  original clips, so player diversity is lower than the coverage plan intended.
  The detectors have two numeric parameters and do not learn player appearance,
  so this is a limitation on diversity, not a leak.
- The ATP Finals video is from the 2023 tournament (uploaded in 2025 by Tennis
  TV), the Rome video is a women's final, and the Wimbledon and US Open matches
  are women's matches, so the test split covers women's and men's tennis.

## Amendment 3: candidate triage by visual review

*Made after the windows were downloaded and before any clip was annotated or run
through a detector.*

An uninterrupted segment of at least 8 s is **not** a rally. Most such segments in
a broadcast are close-ups, crowd shots, player boxes, serve preparation or
changeovers, and a few contain a shot change that the detector missed. The review
therefore added a visual step:

1. For each of the 91 candidates found in the 18 downloaded windows, three frames
   (at 10%, 50% and 90% of the segment) were inspected.
2. A candidate was **accepted** if all three frames show the standard high camera
   behind a baseline with the whole court and the same shot throughout. It was
   **rejected** if it is a close-up, crowd or box shot, a stadium panorama, a low
   or sideline camera angle, a moving or zooming camera, or if the frames show
   different shots (an undetected cut).
3. At most six clips are kept per match, in chronological order; the rest are
   marked `excluded`.
4. Every decision and its reason is recorded in `candidates_review.csv`.

Result: 26 clips accepted (20 in the test split, 6 in development) out of 91
candidates. Frame rates are mixed (23.976, 25, 50 and 59.94 FPS), all clips are
1920x1080, and the clips total about 5 minutes.

Limits of this review: it is a single human judgement made from still frames, not
repeated by a second person; it cannot detect replays or slow motion that look
like a live wide shot; and a clip that turns out to contain no point in play is
rejected at annotation time for that reason.

**Expected size.** At about 4-5 hits per clip the 20 test clips would hold fewer
than the 100 events targeted. This is checked after annotation; if the target is
not met, further windows will be sampled with the same procedure before any
detector is run on the test split.

## Amendment 4: what counts as a contact and as a rally

*Made after the first annotation pass of the test clips was completed and before any
detector was run on them. The threshold was written into the code before the
annotation counts were opened.*

**Annotation convention for the new clips.** Every racket-ball contact of a point is
marked, **including the serve that starts the point, faulted serves, and shots that
go out or into the net**. Contacts after the point has ended (for example a ball
hit away in frustration) are not marked. The two original clips were annotated under
the earlier wording ("while the point is in play"); a faulted serve was not
treated explicitly there, so that wording is superseded by this convention for all
later annotation.

**Rally rule.** A clip is a rally only if it has **at least three** annotated
contacts (a serve, a return and one more). Clips with fewer are moved to the
`rejected` split. A wide shot of a serve and a fault, or of a point cut short, is
not a rally, and the visual triage of Amendment 3 cannot tell the two apart from
still frames. The rule applies to the content of the clip, not to any detector
output.

**Outcome of the first pass.** Of 20 test clips, 14 are rallies (105 contacts,
4 matches) and 6 are rejected (five with 2 contacts, one with 1):

| Match | Clips kept | Contacts |
| --- | ---: | ---: |
| Nitto ATP Finals 2023 | 3 | 29 |
| Roland-Garros 2025 final | 4 | 33 |
| US Open 2026 final | 4 | 26 |
| Wimbledon 2026 | 3 | 17 |
| **Total** | **14** | **105** |

This meets the minimum of 100 events and four matches, but only just, and the
paired comparisons will have wide intervals. More windows can be sampled with
`python -m benchmark.sample_windows <match_id> <duration> --extra 3`, which
continues the original seeded draw without changing the numbering or overlapping
the first windows. Doing so is allowed only before any detector is run on the test
split.

The first-pass annotations are frozen with this change. The second pass (for
inter-annotation agreement) is made later without looking at them.
