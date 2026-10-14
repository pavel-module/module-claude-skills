# Changelog

All notable changes to the **apps-exam-screens** skill.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html),
read for a skill as:

- **MAJOR** — the procedure or a file layout changes in a way that breaks
  existing exam folders, mapping files or screen names;
- **MINOR** — a new capability, a new flag, a new rule in `SKILL.md`;
- **PATCH** — fixes and wording that change no behaviour.

## [Unreleased]

## [1.0.0] — 2026-10-14

First public release. Takes a folder of screen recordings and returns a named,
deduplicated, PII-redacted set of screenshots.

### Added

- `extract_frames.py` — splits recordings into distinct screens by finding
  *settled runs* (stretches where the picture stops changing for longer than
  `--min-stable`), rather than sampling at a fixed interval or using scene
  detection, both of which return piles of mid-animation frames. Drops
  duplicates within and across recordings. The status bar and home indicator are
  excluded from frame comparison, so a passing minute on the clock does not
  count as a new screen. Tunable through `--fps`, `--min-stable`, `--eps-stable`
  and `--eps-dup`, with `--dry-run` to estimate the screen count first.
- `rename_screens.py` — lays selected frames out as
  `XX-AppName-ScenarioName-State.png` from a TSV mapping file, with numbering
  that continues across recordings and runs, and writes `index.md` recording the
  source file and timecode of every screen.
- `redact_screens.py` — redaction of personal data in three modes (`pixelate`,
  `blur`, `fill`), set per row or per zone. `--grid` draws a percentage grid over
  a screen to read zone coordinates off; `--zoom` enlarges a region so
  individual fields inside a document can be marked up; `--preview` outlines the
  zones over the frame so the aim can be checked before anything is painted
  over. Originals are stashed in `.work/originals/`, making redaction idempotent
  and reversible through `--restore`.
- `SKILL.md` — the procedure Claude follows, including what to discard and what
  to keep when reviewing frames, scenario naming rules, and the redaction
  principle: redact the value, keep the interface.

### Notes

- Dependencies are deliberately minimal: ffmpeg and Pillow, nothing else.
- Redaction is manual by design. A detector that finds the face but misses the
  MRZ on the back of an ID is worse than no detector, because it feels like it
  worked.

[Unreleased]: https://github.com/pavel-module/module-claude-skills/compare/apps-exam-screens-v1.0.0...HEAD
[1.0.0]: https://github.com/pavel-module/module-claude-skills/releases/tag/apps-exam-screens-v1.0.0
