# Claude Code skills

Skills I build for my own work and keep here in the open. They come out of
running a small fintech-focused UX studio, so they lean towards research,
teardowns and the unglamorous parts of design work that are worth automating.

Each skill is a self-contained folder: a `SKILL.md` telling Claude how to do the
job, and whatever scripts it needs. No frameworks, no build step — drop the
folder in and it works.

## Skills

| Skill | What it does |
|---|---|
| [apps-exam-screens](apps-exam-screens/) | Turns screen recordings of a mobile app into a named, deduplicated, PII-redacted set of screenshots for UX teardowns |

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
