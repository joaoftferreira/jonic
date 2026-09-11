"""Measure shapes against the real eye outline. Test support, not runtime code.

Picking a gaze distance by eye is how the inner iris ended up buried in the
notch between the two eyes during development. These helpers flatten the
contour into a polygon so a test can ask the only question that matters: after
the gaze moves, how much of each iris and each shine is still visible?
"""
import math
import re

from eyes import geometry as g

_FLATTEN_STEPS = 200          # samples per cubic segment


def _contour_polygon():
    numbers = [float(n) for n in re.findall(r"-?\d+\.?\d*", g.CONTOUR_PATH)]
    points = list(zip(numbers[0::2], numbers[1::2]))
    start = current = points[0]
    curves = []
    for i in range(1, len(points) - 2, 3):
        curves.append((current, points[i], points[i + 1], points[i + 2]))
        current = points[i + 2]
    curves.append((current, current, start, start))      # the closing line
    polygon = []
    for p0, p1, p2, p3 in curves:
        for step in range(_FLATTEN_STEPS):
            t = step / _FLATTEN_STEPS
            u = 1 - t
            polygon.append((
                u**3 * p0[0] + 3*u*u*t * p1[0] + 3*u*t*t * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3*u*u*t * p1[1] + 3*u*t*t * p2[1] + t**3 * p3[1]))
    return polygon


POLYGON = _contour_polygon()


def inside_contour(x, y) -> bool:
    """Even-odd ray cast against the flattened outline."""
    crossings = False
    count = len(POLYGON)
    for i in range(count):
        x1, y1 = POLYGON[i]
        x2, y2 = POLYGON[(i + 1) % count]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) / (y2 - y1) * (x2 - x1):
            crossings = not crossings
    return crossings


def visible_fraction(ellipse, dx=0.0, samples=60) -> float:
    """How much of `ellipse`, shifted by dx, survives the contour clip (0..1)."""
    angle = math.radians(ellipse["rot"])
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    total = visible = 0
    for i in range(samples):
        for j in range(samples):
            u = (i + 0.5) / samples * 2 - 1
            v = (j + 0.5) / samples * 2 - 1
            if u * u + v * v > 1:
                continue                      # outside the unit disc
            px, py = ellipse["rx"] * u, ellipse["ry"] * v
            x = ellipse["cx"] + dx + px * cos_a - py * sin_a
            y = ellipse["cy"] + px * sin_a + py * cos_a
            total += 1
            visible += inside_contour(x, y)
    return visible / total
