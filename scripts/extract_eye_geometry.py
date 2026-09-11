#!/usr/bin/env python3
"""Regenerate software/pi/eyes/geometry.py from art/sonic-eyes.svg.

The art file is an Inkscape drawing: layer 1 is a 360 kB embedded tracing
bitmap we do not want, layer 2 holds the five shapes we do:

    path1031          the white eye contour (both eyes, one outline)
    ellipse1027/1029  the two irises          (rx 6.45, ry 19.89)
    ellipse1029-3/-6  the two iris shines     (rx 2.40, ry  7.75)

Each shape carries its own affine transform, several of which mirror the y
axis. This script bakes every transform into plain coordinates so the runtime
page can drop the shapes straight into an <svg> with no transform of its own,
then writes the result as a Python module.

Run it only when art/sonic-eyes.svg changes:

    python3 scripts/extract_eye_geometry.py
"""
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "art" / "sonic-eyes.svg"
OUT = ROOT / "software" / "pi" / "eyes" / "geometry.py"

SVG_NS = "{http://www.w3.org/2000/svg}"
CONTOUR_ID = "path1031"
# rx of the two irises vs the two shines; used only to tell the pairs apart.
IRIS_RX = 6.0


def parse_matrix(text):
    """'matrix(a,b,c,d,e,f)' -> (a, b, c, d, e, f). Only matrix() is used here."""
    m = re.fullmatch(r"\s*matrix\(([^)]*)\)\s*", text)
    if not m:
        raise ValueError(f"expected a matrix() transform, got {text!r}")
    nums = [float(n) for n in re.split(r"[,\s]+", m.group(1).strip())]
    if len(nums) != 6:
        raise ValueError(f"matrix() needs 6 numbers, got {nums}")
    return tuple(nums)


def apply_point(mat, x, y):
    a, b, c, d, e, f = mat
    return a * x + c * y + e, b * x + d * y + f


def place_ellipse(mat, cx, cy, rx, ry):
    """Bake `mat` into an axis-aligned-plus-rotation ellipse.

    An affine map sends an ellipse to an ellipse, but in general the image
    axes are no longer perpendicular, which a plain <ellipse rotate()> cannot
    express. These four happen to stay perpendicular (Inkscape only ever
    rotated and mirrored them), so we assert that rather than hope."""
    a, b, c, d, _, _ = mat
    ux, uy = a * rx, b * rx          # image of the +x semi-axis
    vx, vy = c * ry, d * ry          # image of the +y semi-axis
    cos = (ux * vx + uy * vy) / (math.hypot(ux, uy) * math.hypot(vx, vy))
    if abs(cos) > 1e-3:
        raise ValueError(f"ellipse axes are not perpendicular after transform "
                         f"(cos={cos:.4g}); it cannot be written as rotate()")
    ncx, ncy = apply_point(mat, cx, cy)
    return {
        "cx": ncx, "cy": ncy,
        "rx": math.hypot(ux, uy), "ry": math.hypot(vx, vy),
        "rot": math.degrees(math.atan2(uy, ux)),
    }


def transform_path(mat, d):
    """Bake `mat` into an M/C/z path's coordinates.

    Only the subset Inkscape emitted here is handled: one absolute moveto, a
    run of absolute cubics, and a close. Anything else raises rather than
    silently producing a wrong outline."""
    tokens = re.findall(r"([MCz])([^MCz]*)", d)
    if [t[0] for t in tokens][:1] != ["M"] or [t[0] for t in tokens][-1:] != ["z"]:
        raise ValueError("path must start with M and end with z")
    out = []
    for cmd, args in tokens:
        if cmd == "z":
            out.append("z")
            continue
        nums = [float(n) for n in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", args)]
        if len(nums) % 2 or (cmd == "C" and len(nums) % 6):
            raise ValueError(f"unexpected argument count for {cmd}: {nums}")
        pts = [apply_point(mat, nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
        out.append(cmd + ",".join(f"{x:.4f},{y:.4f}" for x, y in pts))
    return "".join(out)


def path_bbox(d, steps=400):
    """Tight bbox of an M/C/z path, by flattening every cubic."""
    nums = [float(n) for n in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", d)]
    pts = list(zip(nums[0::2], nums[1::2]))
    start = cur = pts[0]
    segs = []
    for i in range(1, len(pts) - 2, 3):            # each cubic is 3 points
        segs.append((cur, pts[i], pts[i + 1], pts[i + 2]))
        cur = pts[i + 2]
    segs.append((cur, cur, start, start))          # the closing straight line
    xs, ys = [], []
    for p0, p1, p2, p3 in segs:
        for k in range(steps + 1):
            t = k / steps
            u = 1 - t
            xs.append(u**3 * p0[0] + 3*u*u*t * p1[0] + 3*u*t*t * p2[0] + t**3 * p3[0])
            ys.append(u**3 * p0[1] + 3*u*u*t * p1[1] + 3*u*t*t * p2[1] + t**3 * p3[1])
    return min(xs), min(ys), max(xs), max(ys)


def main():
    tree = ET.parse(SVG)
    contour_d = None
    ellipses = []
    for el in tree.iter():
        tag = el.tag.replace(SVG_NS, "")
        mat_attr = el.get("transform")
        if tag == "path" and el.get("id") == CONTOUR_ID:
            contour_d = transform_path(parse_matrix(mat_attr), el.get("d"))
        elif tag == "ellipse":
            ellipses.append(place_ellipse(
                parse_matrix(mat_attr),
                float(el.get("cx")), float(el.get("cy")),
                float(el.get("rx")), float(el.get("ry"))))

    if contour_d is None:
        sys.exit(f"no <path id={CONTOUR_ID}> in {SVG}")
    if len(ellipses) != 4:
        sys.exit(f"expected 4 ellipses in {SVG}, found {len(ellipses)}")

    irises = sorted((e for e in ellipses if e["rx"] >= IRIS_RX), key=lambda e: e["cx"])
    shines = sorted((e for e in ellipses if e["rx"] < IRIS_RX), key=lambda e: e["cx"])
    if len(irises) != 2 or len(shines) != 2:
        sys.exit(f"expected 2 irises and 2 shines, got {len(irises)} and {len(shines)}")

    x0, y0, x1, y1 = path_bbox(contour_d)

    def fmt(e):
        return ("        {{\"cx\": {cx:.4f}, \"cy\": {cy:.4f}, "
                "\"rx\": {rx:.4f}, \"ry\": {ry:.4f}, \"rot\": {rot:.4f}}},"
                ).format(**e)

    OUT.write_text(f'''"""Sonic eye geometry, in SVG user units.

GENERATED by scripts/extract_eye_geometry.py from art/sonic-eyes.svg.
Do not edit by hand; edit the art file and re-run the script.

Every Inkscape transform is already baked into these coordinates, so the
shapes can be dropped into an <svg> as-is. The contour is the white of both
eyes as a single outline; each iris is black and carries a white shine that
must travel with it when the gaze moves.
"""

# Tight bounding box of the contour: (min_x, min_y, width, height).
CONTOUR_BBOX = ({x0:.4f}, {y0:.4f}, {x1 - x0:.4f}, {y1 - y0:.4f})

# Centre of that box. The runtime transform pins this to the middle of the panel.
CONTOUR_CENTER = ({(x0 + x1) / 2:.4f}, {(y0 + y1) / 2:.4f})

CONTOUR_PATH = (
    "{contour_d}"
)

IRISES = [
{fmt(irises[0])}
{fmt(irises[1])}
]

SHINES = [
{fmt(shines[0])}
{fmt(shines[1])}
]
''')
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  contour bbox {x0:.3f},{y0:.3f} {x1 - x0:.3f}x{y1 - y0:.3f}")
    for name, group in (("iris", irises), ("shine", shines)):
        for e in group:
            print(f"  {name:5s} cx={e['cx']:9.4f} cy={e['cy']:9.4f} "
                  f"rx={e['rx']:7.4f} ry={e['ry']:7.4f} rot={e['rot']:6.3f}")


if __name__ == "__main__":
    main()
