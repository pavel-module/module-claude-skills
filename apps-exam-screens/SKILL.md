---
name: apps-exam-screens
description: Turns screen recordings of a mobile app into individual screenshots, removes duplicates, groups them by scenario, redacts personal data and lays them out in screens/ named XX-AppName-ScenarioName-State. Use when asked to break down screen recordings, pull screens out of a video, cut screenshots for an app teardown, or when new recordings are dropped into an assets/ folder.
---

# Screen recordings into screens

## Input and output

An exam folder is any folder with an `assets/` directory of recordings inside it.

```
<exam>/
├── assets/        ← screen recordings, provided by the user, never modify
├── .work/         ← scratch: frames/, thumbs/, grid/, preview/, originals/,
│                    manifest.json, map.tsv, redact.tsv (keep out of git)
└── screens/       ← result: XX-AppName-ScenarioName-State.png + index.md
```

Requires `ffmpeg` in PATH and Python 3.8+ with Pillow. The scripts say what is missing.

## Procedure

Two shell variables used throughout — set them once:

```bash
S=~/.claude/skills/apps-exam-screens/scripts    # where this skill lives
E=path/to/exams/NN-appname                      # the exam folder
```

### 1. Extract frames

```bash
python3 $S/extract_frames.py $E
```

The script samples each recording, catches "settled" frames (the screen holds
still for ≥0.5 s, so the animation has finished), drops duplicates within and
across recordings, extracts them at full resolution into `.work/frames/`, writes
small previews into `.work/thumbs/` and a `.work/manifest.json`.

Knobs, when the result is off:

| Flag | Default | When to turn it |
|---|---|---|
| `--min-stable` | 0.5 | too many mid-animation frames → raise to 0.8–1.0 |
| `--eps-dup` | 0.012 | similar screens got lost → lower to 0.006; too many duplicates → raise to 0.02 |
| `--eps-stable` | 0.004 | scrolling is cut into many fragments → raise |
| `--fps` | 4 | fast taps are missed → raise to 6–8 (slower) |
| `--dry-run` | — | estimate the screen count without extracting frames |

Ten minutes of video takes roughly 1.5–2 minutes.

### 2. Review and select

Look at **`.work/thumbs/*.jpg`**, not the full-resolution frames — context is
cheaper. Read them in batches of 10–15, in id order (which is chronological).

Discard:
- duplicates the script missed: the only difference is the clock, a progress bar
  or a slight scroll offset;
- scrolling through a long document (terms, privacy notice) — one frame of the
  beginning is enough, the other 5–10 frames of the same text are noise;
- blurred frames caught mid-transition or mid-sheet;
- OS screens that are beside the point: home screen, Control Centre, the mail
  app, blank white frames between apps;
- a second splash screen on a later launch when one is already kept;
- a frame with the keyboard up when the same screen without it exists and
  nothing new is visible.

Keep:
- states of one screen: empty / typing / filled / loading / error / success —
  these are different screens and the whole point of the exercise;
- system prompts the app itself triggers (camera, notifications, Face ID, ATT) —
  part of onboarding and a subject of the teardown;
- web views with legal documents and third-party SDKs (Sumsub, Zendesk) — they
  show where the app falls out of its own design;
- transactional emails and support chats if they ended up in the recording.

**Personal data.** Recordings almost always contain an ID document, a selfie, a
phone number, an address, a full name, an email. Do not discard those frames —
they are needed for the teardown — but flag them with `PII` in the fourth column
of the map so they never reach a publication unredacted.

### 3. Mapping file

Write a TSV to `.work/map.tsv`; row order is numbering order. Group by scenario:
the whole onboarding step by step, then the whole KYC flow, and so on — in the
order of the user journey, not the order of recording.

```
f0003	Onboarding	Welcome
f0005	Onboarding	PhoneInput
f0008	Onboarding	OtpSent
f0011	Kyc	DocumentReview	PII
f0014	Kyc
```

Columns: `frame id`, `Scenario`, `State` (optional), `Flag` (optional, currently
only `PII` is used).

Naming rules:
- `XX` — a running number per app that **never resets** between recordings or
  runs. The script continues from the highest number already in `screens/`.
- `AppName` — PascalCase, spelled the way the brand spells it: `Mercuryo`,
  `Revolut`, `AtlanticMoney`.
- `ScenarioName` — PascalCase, 1–3 words, a user journey rather than a UI
  element: `Onboarding`, `KycVerification`, `BuyCrypto`, `Withdraw`, `Settings`.
  One journey, one name — do not breed synonyms (`SignUp` next to `Registration`).
- `State` — optional tail: a state or a step id. `Empty`, `Filled`, `Error`,
  `Loading`, `Success`, `Step2`, `PhoneInput`.

### 4. Lay out

```bash
python3 $S/rename_screens.py $E --app Mercuryo --map $E/.work/map.tsv
```

Copies the frames into `screens/` under their final names and appends to
`screens/index.md` — a table of number, file, scenario, state, source recording
and timecode, so you can always go back to the video. `--reset` wipes `screens/`
and starts from 01.

### 5. Redact personal data

Every frame flagged `PII` goes through redaction — `screens/` must hold clean
files, because those are the ones that reach git and publications.

**The governing principle: redact the value, not the interface.** The screen is
teardown material, so field labels (`Email`, `City`, `Date of birth`), the
document header and type (`TEMPORARY RESIDENCE AND WORK PERMIT`, `DRIVING
LICENCE`), the coat of arms, item numbers, currencies, amounts and list
structure all stay visible. Blanking a whole document is a failure: such a frame
no longer shows what the app was asking for.

Redact:
- photos and faces, full name, date and place of birth, signature;
- document number, personal id number, the MRZ (it repeats everything else);
- **issue and expiry dates** — a date plus an issuing authority identifies the
  holder as well as a number does;
- **name, address and tax numbers of an employer** or any legal entity tied to
  the holder — on residence and work permits that points straight at a person;
- phone number, address, card number, email, other people's names and the
  subject lines of their emails.

When in doubt, redact. A document on the frame must read as *a type of
document*, not as *somebody's document*.

The loop is four steps and the third is not optional:

```bash
# 1. grid across the whole screen
python3 $S/redact_screens.py $E --grid 12 25 48
# 2. for small fields: the same grid enlarged inside a region
#    (percentages still refer to the whole screen)
python3 $S/redact_screens.py $E --grid 25 --zoom 22,30,54,21
# 3. zone outlines over the frame: verify the aim BEFORE redacting
python3 $S/redact_screens.py $E --map $E/.work/redact.tsv --preview --zoom 22,30,54,21
# 4. redact
python3 $S/redact_screens.py $E --map $E/.work/redact.tsv
```

Step 3 is mandatory. Coordinates read off the grid by eye miss by 2–4% on a
regular basis — especially horizontally on documents, where text starts further
left than it looks. On a redacted frame that miss is invisible: everything looks
covered while half a surname sticks out. Two or three `--preview` rounds are
normal and cheap.

Format of `.work/redact.tsv`:

```
12	2,18.3,45,2.4;19,34,76,8.5,blur
25	27,36.3,14,12.3;45,38.3,18,2.4;52.5,43.6,11.5,2.3
```

A zone is `x,y,w,h` in percent of the frame, several separated by `;`. Modes:
`pixelate` (default — a coarse mosaic that destroys the information), `blur`
(tidier over large areas), `fill` — a flat patch in the region's average colour.
A mode can be set for a whole row in the third column or per zone as a fifth
value. One screen, one row.

Originals are kept in `.work/originals/` and redaction always starts from the
clean frame, so fixing coordinates and running again never stacks mosaic on
mosaic. `--restore 25` or `--restore all` brings the originals back.

When fields are many and tightly packed — a driving licence, which has no field
labels at all — covering the whole block with one zone is more honest than
chasing every line: the header, the coat of arms and the item numbers stay
visible, and that is the structure of the document.

### 6. Report

How many screens, which scenarios they fall into, what was discarded and why,
how many megabytes `screens/` weighs, how many frames carried personal data and
what was redacted on them.

## Never

- Never overwrite or delete anything in `assets/` — those are the source files.
- Never commit `.work/` or `assets/`. Recordings run to gigabytes and must not
  enter git; only `screens/` belongs in the repository. If the project does not
  ignore them yet, add `**/.work/` and the path to `assets/` to `.gitignore`.
- Never invent scenario names when the frames show what the app calls the step —
  use the app's own wording.
- Never renumber files already in `screens/` when new recordings are added. The
  numbering is continuous and stable; teardown write-ups refer to it.
