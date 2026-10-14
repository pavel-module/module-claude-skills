# Claude Code skills

Skills I build for my own work and keep here in the open. They come out of
running a small fintech-focused UX studio, so they lean towards research,
teardowns and the unglamorous parts of design work that are worth automating.

Each skill is a self-contained folder: a `SKILL.md` telling Claude how to do the
job, and whatever scripts it needs. No frameworks, no build step — drop the
folder in and it works.

## Skills

| Skill | Version | What it does |
|---|---|---|
| [apps-exam-screens](apps-exam-screens/) | [1.0.0](apps-exam-screens/CHANGELOG.md) | Turns screen recordings of a mobile app into a named, deduplicated, PII-redacted set of screenshots for UX teardowns |

## Install

Clone the repository and symlink the skills you want into your Claude Code
skills folder:

```bash
git clone https://github.com/pavel-module/module-claude-skills.git
ln -s "$PWD/module-claude-skills/apps-exam-screens" ~/.claude/skills/apps-exam-screens
```

A symlink means one copy on the machine: pull the repo and every project sees
the update. Copying the folder works too, but copies drift.

Per-project install is the same thing pointed at `<project>/.claude/skills/`.

Each skill lists its own requirements in its README. Nothing here needs more
than ffmpeg and Pillow.

## Versioning

Each skill is versioned on its own, because each is installed on its own. A
skill's version says nothing about the others, and the repository has no version
of its own.

Versions follow [SemVer](https://semver.org/), read for a skill as:

- **MAJOR** — the procedure or file layout changes in a way that breaks existing
  work: folder structure, mapping file format, output naming;
- **MINOR** — a new capability, flag or rule;
- **PATCH** — fixes and wording that change no behaviour.

Every skill keeps a `CHANGELOG.md`. Releases are tagged `<skill>-vX.Y.Z` and
published under [Releases](https://github.com/pavel-module/module-claude-skills/releases),
so a release always names the skill it belongs to.

To update an installed skill, pull the repository — a symlinked skill follows
along. To pin a version, check out its tag instead:

```bash
git checkout apps-exam-screens-v1.0.0
```

<details>
<summary>Cutting a release</summary>

1. Move the entries from `## [Unreleased]` into a new version heading in the
   skill's `CHANGELOG.md`, with today's date.
2. Bump the version line in the skill's `SKILL.md` and `README.md`.
3. Commit, then tag and publish, taking the notes straight from the changelog
   section so the two can never disagree:

```bash
SKILL=apps-exam-screens
VERSION=1.2.0
awk -v v="$VERSION" '$0 ~ "^## \\["v"\\]" {f=1; next} /^## \[/ {f=0} f' \
  "$SKILL/CHANGELOG.md" > /tmp/notes.md

git tag "$SKILL-v$VERSION"
git push origin "$SKILL-v$VERSION"
gh release create "$SKILL-v$VERSION" --title "$SKILL $VERSION" --notes-file /tmp/notes.md
```
</details>

## What a skill is

A [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) is a
folder with a `SKILL.md` whose front matter describes when it applies. Claude
loads the instructions when the task matches and follows them instead of
improvising. Scripts next to it do the deterministic work; the judgement calls
stay with the model.

That split is the point of these skills. Extracting frames from a video is
mechanical and belongs in a script. Deciding that two frames are the same screen
in different states, or that a surname is still showing through a redaction, is
not — so the skills are written to hand each part to whichever is better at it.

## Licence

MIT. Use them, change them, ship them.

---

Built by [Pavel Chelyuskin](https://www.linkedin.com/in/paveliche) at
[Module Agency](https://www.module.agency) — UX for fintech.
