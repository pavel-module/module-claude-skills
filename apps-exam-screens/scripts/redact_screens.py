#!/usr/bin/env python3
"""Redact personal data on finished screens.

There is deliberately no auto-detection: a missed passport costs more than a
minute of manual work. Zones are set by the agent after looking at the screen
with a coordinate grid drawn over it.

Four steps:
  1. --grid 25 28 48      -> writes previews with a percentage grid to .work/grid/
     --grid 25 --zoom 22,30,54,21 -> same grid, enlarged inside a region, so you
     can mark up individual fields of a document instead of blanking all of it
  2. edit .work/redact.tsv
  3. --map .work/redact.tsv --preview -> zone outlines over the frame, destroys nothing
  4. --map .work/redact.tsv -> redacts and overwrites the files in screens/

Do not skip step 3: coordinates read off the grid by eye miss by 2-4% every
other time, and on a redacted frame you can no longer tell.

Originals are moved to .work/originals/ (kept out of git), which makes redaction
idempotent: a rerun with corrected coordinates starts from the clean original
instead of stacking redaction over redaction. --restore brings an original back.

Format of .work/redact.tsv - screen, zones, mode (optional):

    25	8,14,84,38	pixelate
    48	0,13,100,8;0,21,100,8
    52	3,20,60,5	fill

Screen: its number, a fragment of the file name, or the whole file name.
Zone: x,y,w,h as percentages of frame width/height, several separated by `;`.
Modes: pixelate (default, irreversible), blur, fill (flat patch).
A zone can carry its own mode as a fifth value: `0,32,100,61,blur`.
One screen, one row: a repeated row overwrites the previous one.
"""
import argparse
import math
import re
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    sys.exit("Pillow is required: python3 -m pip install Pillow")

FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",            # macOS
    "/System/Library/Fonts/Helvetica.ttc",                          # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",         # Debian/Ubuntu
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",       # Fedora
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",                     # Arch
    "C:/Windows/Fonts/arialbd.ttf",                                 # Windows
]


def font(size):
    for p in FONT_PATHS:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    try:                                   # Pillow 10.1+ accepts a size for the default font
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def resolve(exam, target):
    """Screen number / name fragment / file name -> path inside screens/."""
    sd = exam / "screens"
    files = sorted(p for p in sd.iterdir() if p.suffix.lower() in (".png", ".jpg"))
    t = target.strip()
    if (sd / t).exists():
        return sd / t
    if re.fullmatch(r"\d+", t):
        n = int(t)
        for p in files:
            m = re.match(r"(\d+)-", p.name)
            if m and int(m.group(1)) == n:
                return p
    hits = [p for p in files if t.lower() in p.name.lower()]
    if len(hits) == 1:
        return hits[0]
    sys.exit(f"cannot tell which screen is meant: {target!r}" +
             (f" ({len(hits)} candidates)" if hits else ""))


MODES = ("pixelate", "blur", "fill")


def parse_boxes(spec, default_mode):
    boxes = []
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        cells = [c.strip() for c in part.split(",")]
        mode = default_mode
        if cells and cells[-1] in MODES:
            mode = cells.pop()
        if len(cells) != 4:
            sys.exit(f"a zone must be x,y,w,h[,mode] in percent, got {part!r}")
        boxes.append((*[float(c) for c in cells], mode))
    return boxes


def apply_boxes(img, boxes):
    for x, y, w, h, mode in boxes:
        X, Y = int(x / 100 * img.width), int(y / 100 * img.height)
        W, H = int(w / 100 * img.width), int(h / 100 * img.height)
        X, Y = max(0, X), max(0, Y)
        W, H = min(W, img.width - X), min(H, img.height - Y)
        if W <= 0 or H <= 0:
            continue
        region = img.crop((X, Y, X + W, Y + H))
        if mode == "pixelate":
            # Block of at least 8 px: a fine mosaic over a line of text stays readable.
            k = max(8, min(W, H) // 5)
            small = region.resize((max(1, math.ceil(W / k)), max(1, math.ceil(H / k))),
                                  Image.BILINEAR)
            region = small.resize((W, H), Image.NEAREST)
        elif mode == "blur":
            region = region.filter(ImageFilter.GaussianBlur(max(12, min(W, H) / 5)))
        else:
            avg = region.resize((1, 1), Image.BILINEAR).getpixel((0, 0))
            region = Image.new(img.mode, (W, H), avg)
        img.paste(region, (X, Y))
    return img


def grid_step(span):
    """Grid step in percent: the narrower the region, the finer the step."""
    return 1 if span <= 25 else (2 if span <= 60 else 5)


def make_grid(src, out, width=460, zoom=None):
    """Preview with a grid. Labels are always percentages OF THE WHOLE screen, so
    coordinates read off a zoomed view can go into redact.tsv unchanged."""
    img = Image.open(src).convert("RGB")
    ox, oy, sx, sy = 0.0, 0.0, 100.0, 100.0
    if zoom:
        ox, oy, sx, sy = zoom
        W0, H0 = img.size
        img = img.crop((int(ox / 100 * W0), int(oy / 100 * H0),
                        int((ox + sx) / 100 * W0), int((oy + sy) / 100 * H0)))
    img = img.resize((width, max(1, int(img.height * width / img.width))), Image.LANCZOS)
    d = ImageDraw.Draw(img, "RGBA")
    f = font(11)
    for axis, off, span, length in (("x", ox, sx, img.width), ("y", oy, sy, img.height)):
        step = grid_step(span)
        label_every = 5 if step == 1 else step
        pct = math.ceil(off / step) * step
        while pct <= off + span + 1e-6:
            pos = (pct - off) / span * length
            major = pct % (label_every * 2 if step == 1 else label_every * 5) == 0
            col = (255, 0, 0, 170) if major else (255, 0, 0, 55)
            if axis == "x":
                d.line([(pos, 0), (pos, img.height)], fill=col, width=1)
            else:
                d.line([(0, pos), (img.width, pos)], fill=col, width=1)
            if pct % label_every == 0:
                at = (pos + 2, 2) if axis == "x" else (2, pos + 2)
                d.text(at, str(int(pct)), fill=(255, 0, 0, 255), font=f,
                       stroke_width=2, stroke_fill=(255, 255, 255, 220))
            pct += step
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)


def draw_preview(src, boxes, out, width=440, zoom=None):
    img = Image.open(src).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img, "RGBA")
    f = font(max(14, W // 50))
    for i, (x, y, w, h, _) in enumerate(boxes, 1):
        X, Y = x / 100 * W, y / 100 * H
        box = (X, Y, X + w / 100 * W, Y + h / 100 * H)
        d.rectangle(box, outline=(255, 0, 0, 255), width=max(2, W // 400))
        d.text((X + 3, Y + 3), str(i), fill=(255, 0, 0, 255), font=f,
               stroke_width=3, stroke_fill=(255, 255, 255, 230))
    if zoom:
        zx, zy, zw, zh = zoom
        img = img.crop((int(zx / 100 * W), int(zy / 100 * H),
                        int((zx + zw) / 100 * W), int((zy + zh) / 100 * H)))
    img = img.resize((width, max(1, int(img.height * width / img.width))), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)


def mark_index(exam, names):
    """Record in index.md that personal data on the screen is already hidden."""
    idx = exam / "screens" / "index.md"
    if not idx.exists():
        return
    lines = []
    for line in idx.read_text().splitlines():
        if any(f"| {n} |" in line for n in names) and "| PII |" in line:
            line = line.replace("| PII |", "| PII, redacted |")
        lines.append(line)
    idx.write_text("\n".join(lines) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("exam", type=Path)
    p.add_argument("--grid", nargs="+", metavar="SCREEN",
                   help="build previews with a coordinate grid for these screens")
    p.add_argument("--zoom", metavar="X,Y,W,H",
                   help="with --grid or --preview: show only this region of the screen "
                        "(in percent) enlarged, to mark up small fields")
    p.add_argument("--map", type=Path, help="TSV with redaction zones")
    p.add_argument("--preview", action="store_true",
                   help="with --map: outline the zones in .work/preview/ instead of redacting")
    p.add_argument("--mode", default="pixelate", choices=list(MODES),
                   help="default mode when a row or zone does not set its own")
    p.add_argument("--restore", nargs="+", metavar="SCREEN",
                   help="restore the originals of these screens (or all)")
    a = p.parse_args()

    originals = a.exam / ".work" / "originals"
    zoom = None
    if a.zoom:
        zoom = [float(v) for v in a.zoom.split(",")]
        if len(zoom) != 4:
            sys.exit("--zoom takes x,y,w,h in percent")

    if a.grid:
        for t in a.grid:
            src = resolve(a.exam, t)
            base = originals / src.name
            suffix = "-zoom" if zoom else ""
            out = a.exam / ".work" / "grid" / (src.stem + suffix + ".jpg")
            make_grid(base if base.exists() else src, out, zoom=zoom)
            print(out)
        return

    if a.restore:
        targets = (sorted(originals.iterdir()) if a.restore == ["all"]
                   else [originals / resolve(a.exam, t).name for t in a.restore])
        for b in targets:
            if not b.exists():
                sys.exit(f"no original for {b.name}")
            shutil.copy2(b, a.exam / "screens" / b.name)
            print(f"restored {b.name}")
        return

    if not a.map:
        sys.exit("one of --map, --grid or --restore is required")

    originals.mkdir(parents=True, exist_ok=True)
    done = []
    for line in a.map.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cells = [c.strip() for c in line.split("\t")] + ["", ""]
        dst = resolve(a.exam, cells[0])
        boxes = parse_boxes(cells[1], cells[2] or a.mode)
        base = originals / dst.name
        if a.preview:
            out = a.exam / ".work" / "preview" / (dst.stem + ".jpg")
            draw_preview(base if base.exists() else dst, boxes, out, zoom=zoom)
            print(f"{out}  {len(boxes)} zones")
            continue
        if not base.exists():                      # first run: stash the original
            shutil.copy2(dst, base)
        img = apply_boxes(Image.open(base).convert("RGB"), boxes)
        img.save(dst)
        done.append(dst.name)
        modes = ", ".join(sorted({b[4] for b in boxes}))
        print(f"{dst.name}: {len(boxes)} zones ({modes})")

    if a.preview:
        return
    mark_index(a.exam, done)
    print(f"\n{len(done)} screens processed, originals in {originals}")


if __name__ == "__main__":
    main()
