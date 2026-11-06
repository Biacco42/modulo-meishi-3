#!/usr/bin/env python3
"""Export the project footprints to one A4 SVG for a 1:1 print check.

Usage: python3 scripts/export_library_print.py [output.svg]

Runs `kicad-cli fp export svg` on modulo-meishi-3/lib/modulo-meishi-3.pretty
and places the footprints at true size on an A4 page with a 50 mm scale bar.
Set KICAD_CLI if kicad-cli is not on PATH or in the default macOS location.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "modulo-meishi-3" / "lib" / "modulo-meishi-3.pretty"
DEFAULT_OUT = ROOT / "docs" / "library-1to1.svg"
LAYERS = "F.Cu,F.SilkS,F.Fab,F.CrtYd,Edge.Cuts,Dwgs.User,B.SilkS,B.Fab"

# (footprint name, x mm, y mm, caption) on the A4 page
PLACEMENT = [
    ("modulo-dev-board_Rev0.3", 20, 40,
     "U1 modulo dev board Rev 0.3（外形 40.64 × 17.78 mm、SWD の切り欠き、Dwgs.User に禁止領域）"),
    ("BatteryClip_Keystone_82_Pair_1xAAA", 20, 110,
     "BT1 Keystone 82 × 2 + 単4形（穴 Ø1.9 mm、0 / 7.6 / 35.0 / 42.6 mm）"),
]


def find_kicad_cli():
    for cand in (os.environ.get("KICAD_CLI"), shutil.which("kicad-cli"),
                 "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"):
        if cand and Path(cand).exists():
            return cand
    sys.exit("kicad-cli not found; set KICAD_CLI")


def inner_svg(path):
    """Return (width_mm, height_mm, viewBox, body) of a KiCad SVG."""
    text = Path(path).read_text(encoding="utf-8")
    m = re.search(r'<svg\b[^>]*?width="([\d.]+)mm"\s+height="([\d.]+)mm"\s+'
                  r'viewBox="([^"]+)"[^>]*>(.*)</svg>', text, re.S)
    if not m:
        sys.exit(f"unexpected SVG header in {path}")
    w, h, vb, body = m.groups()
    body = re.sub(r"<title>.*?</title>|<desc>.*?</desc>", "", body, flags=re.S)
    return float(w), float(h), vb, body


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    cli = find_kicad_cli()
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([cli, "fp", "export", "svg", "-o", tmp, "--layers", LAYERS,
                        "--sp", "--black-and-white", str(LIB)],
                       check=True, stdout=subprocess.DEVNULL)
        parts = []
        for name, x, y, caption in PLACEMENT:
            w, h, vb, body = inner_svg(Path(tmp) / f"{name}.svg")
            parts.append(
                f'<text x="{x}" y="{y - 4}" font-size="3">{caption}</text>\n'
                f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{vb}">'
                f'{body}</svg>')
    ticks = "".join(
        f'<line x1="{20 + i * 10}" y1="270" x2="{20 + i * 10}" y2="{266 if i % 5 == 0 else 268}" '
        f'stroke="#000" stroke-width="0.2"/>' for i in range(6))
    page = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297"
     font-family="sans-serif">
<rect width="210" height="297" fill="#fff"/>
<text x="20" y="18" font-size="5">meishi 3 ライブラリの 1:1 確認</text>
<text x="20" y="25" font-size="3">「実際のサイズ」（拡大縮小なし、100 %）で印刷し、下の 50 mm の目盛りを定規で測ってから実物を当てる。</text>
{"".join(parts)}
<line x1="20" y1="270" x2="70" y2="270" stroke="#000" stroke-width="0.3"/>
{ticks}
<text x="20" y="276" font-size="3">50 mm</text>
</svg>
'''
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
