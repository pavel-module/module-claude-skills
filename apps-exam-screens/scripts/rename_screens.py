#!/usr/bin/env python3
"""Lay the selected frames out in screens/ under their final names.

Input is a mapping file (TSV) written by the agent after reviewing the frames.
Row order is numbering order. Row format:

    f0007<TAB>Onboarding<TAB>EmptyState
    f0008<TAB>Onboarding
    f0009<TAB>Kyc<TAB>DocumentReview<TAB>PII

The fourth column is an optional flag that lands in index.md (PII means the
frame carries personal data and must not go into any publication unredacted).

Numbering is continuous per app: it resumes from the highest number already in
screens/. Frames missing from the map do not reach screens/.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def pascal(s):
    """ScenarioName -> ScenarioName, scenario name -> ScenarioName."""
    parts = re.split(r"[^0-9A-Za-z]+", s.strip())
    return "".join(p[:1].upper() + p[1:] if p else "" for p in parts)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("exam", type=Path, help="exam folder")
    p.add_argument("--app", required=True, help="AppName used in file names, e.g. Mercuryo")
    p.add_argument("--map", required=True, type=Path, help="TSV: frame_id, scenario, state, flag")
    p.add_argument("--reset", action="store_true", help="wipe screens/ and start from 01")
    a = p.parse_args()

    work = a.exam / ".work"
    manifest = {m["id"]: m for m in json.loads((work / "manifest.json").read_text())}
    screens = a.exam / "screens"
    screens.mkdir(parents=True, exist_ok=True)

    if a.reset:
        for f in screens.iterdir():
            f.unlink()

    nums = [int(m.group(1)) for f in screens.iterdir()
            if (m := re.match(r"(\d+)-", f.name))]
    n = max(nums, default=0)

    rows = []
    for line in a.map.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cells = [c.strip() for c in line.split("\t")] + ["", "", ""]
        fid, scenario, state, flag = cells[0], cells[1], cells[2], cells[3]
        if fid not in manifest:
            sys.exit(f"frame {fid} is not in the manifest")
        src = work / manifest[fid]["file"]
        n += 1
        stem = f"{n:02d}-{a.app}-{pascal(scenario)}"
        if state:
            stem += f"-{pascal(state)}"
        dst = screens / (stem + src.suffix)
        shutil.copy2(src, dst)
        rows.append((n, dst.name, scenario, state, flag, manifest[fid]))
        print(dst.name)

    index = screens / "index.md"
    head = (f"# Screens - {a.app}\n\n"
            "| # | File | Scenario | State | Flag | Source | t, s |\n"
            "|---|---|---|---|---|---|---|\n")
    body = "".join(
        f"| {num} | {name} | {sc} | {st or '—'} | {fl or '—'} | {m['video']} | {m['t']} |\n"
        for num, name, sc, st, fl, m in rows)
    if index.exists() and not a.reset:
        index.write_text(index.read_text().rstrip("\n") + "\n" + body)
    else:
        index.write_text(head + body)
    print(f"\n{len(rows)} screens -> {screens}")


if __name__ == "__main__":
    main()
