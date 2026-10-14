# apps-exam-screens

A Claude Code skill that turns screen recordings of a mobile app into a clean,
named set of screenshots: it cuts the video into distinct screens, removes
duplicates, groups them by user journey, redacts personal data and lays
everything out with an index that points back to the source timecode.

Built for UX teardowns, where the raw material is a ten-minute screen recording
and what you actually need is forty labelled screens.

## Install

Copy the `apps-exam-screens` folder into either:

- `~/.claude/skills/` — available in every project;
- `<project>/.claude/skills/` — that project only.

Claude Code picks the skill up on the next session.

## Requirements

| What | Why | Install |
|---|---|---|
| ffmpeg + ffprobe | frame extraction | `brew install ffmpeg` · `apt install ffmpeg` · `winget install ffmpeg` |
| Python 3.8+ | the scripts | usually already there |
| Pillow | grid, previews, redaction | `python3 -m pip install Pillow` |

Nothing else — no numpy, no OpenCV, no ImageMagick. The scripts check their
dependencies on start and name what is missing.

Works on macOS, Linux and Windows. The font used for grid labels is looked up in
the system font paths of all three, falling back to Pillow's built-in font.

## Use

Create a folder for the teardown, drop the recordings into `assets/`, and ask
Claude to break them down:

```
exams/01-appname/
└── assets/
    ├── ScreenRecording_1.mp4
    └── ScreenRecording_2.mp4
```

Claude then follows the procedure in `SKILL.md`: extracts the frames, reviews
them, groups them by scenario, redacts personal data and lays the result out in
`screens/` next to an `index.md` giving the source file and timecode of every
screen.

```
exams/01-appname/screens/
├── 01-AppName-AppStore-Listing.png
├── 02-AppName-Launch-Splash.png
├── 03-AppName-SignIn-Empty.png
├── ...
└── index.md
```

The scripts also run standalone, without Claude — each has `--help`.

## How the extraction works

Not "a frame every N seconds" and not scene detection: both produce piles of
frames caught mid-animation. The script samples the video in grayscale and looks
for *settled runs* — stretches where the picture stops changing for longer than
half a second, meaning the transition has finished. One frame is taken from each
run, then duplicates are dropped within and across recordings. The status bar
and home indicator are excluded from the comparison, otherwise every passing
minute on the clock would count as a new screen.

On a 1260×2736 recording this yields ~90 candidate screens from 11 minutes of
video in about 25 seconds of analysis.

## How redaction works

There is deliberately no face or text auto-detection. A detector that finds the
face but misses the MRZ on the back of an ID is worse than useless, because it
feels like it worked. Instead the skill gives the agent a coordinate grid to
read zones off, a zoom to mark up individual fields inside a document, and an
outline preview to verify the aim before anything is painted over.

The rule it follows: redact the value, keep the interface. Field labels, the
document type, the header and the layout stay readable, because that is what
makes the screenshot worth keeping.

Originals are stashed in `.work/originals/`, so redaction is idempotent and
reversible with `--restore`.

## Files

| File | What it does |
|---|---|
| `SKILL.md` | the procedure and the rules: what to discard, how to name, what to redact |
| `scripts/extract_frames.py` | video → unique screen frames |
| `scripts/rename_screens.py` | selected frames → `screens/` + `index.md` |
| `scripts/redact_screens.py` | coordinate grid, zone preview, redaction |
