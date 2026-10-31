# Project history and origin

## Version history

| Version | Commit | Main result |
| --- | --- | --- |
| `initial-baseline` | `a3bb1a0` | Tutorial-based pipeline before the evaluation and engineering work. |
| `v0.2` | `cecc0e9` | Reusable pipeline, source-video FPS, CLI, validation, safer caches, pinned dependencies, and removal of generated artifacts from the tracked tree. |
| `v0.3` | `dfd62f0` | Player-statistics logic extracted, corrected, clarified, and covered by automated tests. |
| `v0.5` | `ed1f8bc` | Video-separated benchmark, one-to-one event evaluation, development-set error analysis, and measured shot-detection improvement. |
| `v0.6` | `e65b6bf` | Shot-detection thresholds normalized by video FPS while preserving the v0.5 results at 25 FPS. |
| Post-v0.6 | `74f7430` onward | History cleanup, structured CSV export, notebook cleanup, CI, redesigned overlays, model documentation, licensing, visual demo, and clean-clone verification. |
| `v1.0` | `1b4bf16` | Release with the ball checkpoint distributed as a release asset. |

There is intentionally no `v0.4` tag. The benchmark implementation and the
measured v0.5 improvement were committed together, so the repository does not
contain a separate, honest v0.4 snapshot to tag retroactively.

## Project origin

The initial pipeline was built by following a YouTube tutorial. The current
work extends that starting point through pipeline validation, safer detection
caching, automated tests, a reproducible evaluation workflow, manual benchmark
annotations, development-set error analysis, and a quantitatively tested shot
detection improvement. The shot-event thresholds have also been normalized for
different video frame rates.

The tutorial baseline and its original pretrained court model are available in
[Abdullah Tarek's tennis analysis repository](https://github.com/abdullahtarek/tennis_analysis).

### Work beyond the tutorial

- a reusable CLI pipeline, validation, source-FPS handling, and
  content-addressed detection caches;
- corrected player statistics and a structured per-frame CSV export;
- a manually annotated 54-event benchmark split by source video;
- one-to-one temporal event matching and development-only error analysis that
  improved held-out shot-detection F1 from `0.5806` to `0.6875` (see the
  [benchmark](../benchmark/README.md) for the small-sample caveats);
- FPS-normalized detection thresholds that preserve the frozen 25 FPS results;
- automated tests, GitHub Actions, and a verified clean-clone setup;
- stable player roles, redesigned overlays, a mini court, and a visual demo;
- repository-history cleanup, model documentation, and explicit licensing and
  attribution.

## Clean-clone verification

On 23 August 2026, commit `7b310b6` was cloned into a new temporary directory
and tested on an Intel Mac running macOS 12.7.6 with Python 3.11.9. A fresh
virtual environment was created exclusively from the README instructions and
`requirements.txt`.

The dependency installation completed successfully, `pip check` reported no
conflicts, the pinned OpenCV, PyTorch, Torchvision, and Ultralytics packages
imported correctly, all automated tests passed, and `python main.py --help`
completed successfully. The CLI also reported the missing input and three
required model files clearly when run without local assets.

This verifies the clean setup, dependency set, tests, and command-line entry
point. Running a complete video analysis additionally requires the three local
assets documented in [assets-and-training.md](assets-and-training.md) and an
input video.

## v1.0 release verification

The `v1.0` release includes the documented ball checkpoint as a release asset,
without adding model weights to the Git history. Its identity can be checked
against the SHA-256 in [assets-and-training.md](assets-and-training.md). The
final local end-to-end smoke test produced a readable 575-frame, 25 FPS,
1280x720 annotated video and a complete 575-row CSV.
