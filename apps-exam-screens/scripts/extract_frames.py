#!/usr/bin/env python3
"""Split screen recordings into distinct app screens.

How it works: sample the video at a low frame rate in grayscale, find "settled"
runs (the screen stays unchanged for N seconds, which means the animation has
finished and this is a real screen rather than a mid-transition frame), take one
frame from each run, then drop duplicates across runs and across recordings.

Dependencies: ffmpeg/ffprobe and the Python standard library, nothing else.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

for _tool in ("ffmpeg", "ffprobe"):
    if shutil.which(_tool) is None:
        sys.exit(f"{_tool} is required in PATH: brew install ffmpeg "
                 "(Linux: apt install ffmpeg, Windows: winget install ffmpeg)")

SIG_W, SIG_H = 32, 64          # sampling grid used to build a frame signature
PROBE_W = 160                  # width each frame is scaled down to for analysis


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def probe(video):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height",
               "-show_entries", "format=duration", "-of", "json", str(video)]).stdout
    d = json.loads(out)
    s = d["streams"][0]
    return int(s["width"]), int(s["height"]), float(d["format"]["duration"])


def signatures(video, w, h, fps):
    """Yield (t_sec, signature) for frames sampled at the given fps."""
    pw = PROBE_W
    ph = max(2, int(round(h * pw / w / 2)) * 2)
    cmd = ["ffmpeg", "-v", "error", "-i", str(video),
           "-vf", f"fps={fps},scale={pw}:{ph},format=gray", "-f", "rawvideo", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    fsize = pw * ph
    # Ignore the status bar at the top and the home indicator at the bottom:
    # the clock and indicators change on their own and break frame comparison.
    top, bot = int(ph * 0.05), int(ph * 0.97)
    rows = [top + (bot - top) * i // SIG_H for i in range(SIG_H)]
    cols = [pw * j // SIG_W for j in range(SIG_W)]
    offsets = [r * pw + c for r in rows for c in cols]
    i = 0
    try:
        while True:
            buf = proc.stdout.read(fsize)
            if len(buf) < fsize:
                break
            yield i / fps, bytes(buf[o] for o in offsets)
            i += 1
    finally:
        proc.stdout.close()
        proc.wait()


def dist(a, b):
    """Normalised mean brightness difference, 0..1."""
    return sum(abs(x - y) for x, y in zip(a, b)) / (len(a) * 255)


def find_runs(video, fps, eps_stable, min_stable):
    """Find settled runs. Returns [(t_sec, signature, dur_sec)]."""
    w, h, _ = probe(video)
    runs, ref, members = [], None, []

    def close():
        if not members:
            return
        dur = members[-1][0] - members[0][0] + 1.0 / fps
        if dur >= min_stable:
            # Take the frame 60% into the run: the animation has definitely
            # finished and the next tap has not started yet.
            t, sig = members[int(len(members) * 0.6)]
            runs.append((t, sig, dur))

    for t, sig in signatures(video, w, h, fps):
        if ref is None or dist(sig, ref) > eps_stable:
            close()
            ref, members = sig, [(t, sig)]
        else:
            members.append((t, sig))
    close()
    return runs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("exam", type=Path, help="exam folder (must contain assets/)")
    p.add_argument("--fps", type=float, default=4.0, help="sampling rate used for analysis")
    p.add_argument("--eps-stable", type=float, default=0.004,
                   help="threshold for 'frame unchanged' within a run")
    p.add_argument("--min-stable", type=float, default=0.5,
                   help="how many seconds the screen must hold still to count as a screen")
    p.add_argument("--eps-dup", type=float, default=0.012,
                   help="threshold for 'same screen as one already kept'")
    p.add_argument("--format", default="png", choices=["png", "jpg"])
    p.add_argument("--dry-run", action="store_true",
                   help="analyse and report only, do not extract frames")
    a = p.parse_args()

    assets = a.exam / "assets"
    videos = sorted(f for f in assets.iterdir()
                    if f.suffix.lower() in (".mp4", ".mov", ".m4v", ".webm"))
    if not videos:
        sys.exit(f"no video files in {assets}")

    work = a.exam / ".work"
    frames_dir, thumbs_dir = work / "frames", work / "thumbs"
    if not a.dry_run:
        for d in (frames_dir, thumbs_dir):
            d.mkdir(parents=True, exist_ok=True)
            for old in d.iterdir():
                old.unlink()
    work.mkdir(parents=True, exist_ok=True)

    kept, report = [], []
    for v in videos:
        runs = find_runs(v, a.fps, a.eps_stable, a.min_stable)
        taken = 0
        for t, sig, dur in runs:
            if any(dist(sig, k["sig"]) < a.eps_dup for k in kept):
                continue
            kept.append({"video": v.name, "t": t, "dur": dur, "sig": sig})
            taken += 1
        report.append(f"{v.name}: {len(runs)} settled runs -> {taken} unique screens")
        print(report[-1], flush=True)

    manifest = []
    for i, k in enumerate(kept, 1):
        fid = f"f{i:04d}"
        manifest.append({"id": fid, "video": k["video"],
                         "t": round(k["t"], 3), "stable_sec": round(k["dur"], 2),
                         "file": f"frames/{fid}.{a.format}"})

    if not a.dry_run:
        for m in manifest:
            src = assets / m["video"]
            out = frames_dir / f"{m['id']}.{a.format}"
            q = ["-q:v", "2"] if a.format == "jpg" else []
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(m["t"]), "-i", str(src),
                 "-frames:v", "1", *q, str(out)])
            run(["ffmpeg", "-v", "error", "-y", "-i", str(out),
                 "-vf", "scale=300:-1", "-q:v", "4",
                 str(thumbs_dir / f"{m['id']}.jpg")])
            print(f"  {m['id']}  {m['video']}  t={m['t']}s", flush=True)

    (work / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (work / "report.txt").write_text("\n".join(report) + f"\n\ntotal screens: {len(manifest)}\n")
    print(f"\ntotal screens: {len(manifest)}")
    print(f"manifest: {work / 'manifest.json'}")


if __name__ == "__main__":
    main()
