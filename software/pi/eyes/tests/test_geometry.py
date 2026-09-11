"""The geometry module is generated, so these tests guard the regeneration:
if someone re-runs the extractor against edited art and the shapes stop making
sense, the failure lands here rather than on the LCD during the party."""
import re

from eyes import geometry as g


def test_contour_bbox_matches_the_path():
    x0, y0, w, h = g.CONTOUR_BBOX
    nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", g.CONTOUR_PATH)]
    xs, ys = nums[0::2], nums[1::2]
    # Control points can sit outside the curve, so the box is a lower bound on
    # their spread but must still contain every on-curve extreme.
    assert min(xs) <= x0 + 2 and max(xs) >= x0 + w - 2
    assert min(ys) <= y0 + 2 and max(ys) >= y0 + h - 2


def test_contour_center_is_the_middle_of_the_bbox():
    x0, y0, w, h = g.CONTOUR_BBOX
    assert g.CONTOUR_CENTER == (round(x0 + w / 2, 4), round(y0 + h / 2, 4))


def test_two_irises_and_two_shines_ordered_left_to_right():
    assert len(g.IRISES) == 2 and len(g.SHINES) == 2
    assert g.IRISES[0]["cx"] < g.IRISES[1]["cx"]
    assert g.SHINES[0]["cx"] < g.SHINES[1]["cx"]


def test_each_shine_sits_inside_its_iris():
    for iris, shine in zip(g.IRISES, g.SHINES):
        assert shine["rx"] < iris["rx"] and shine["ry"] < iris["ry"]
        assert abs(shine["cx"] - iris["cx"]) < iris["rx"]
        assert abs(shine["cy"] - iris["cy"]) < iris["ry"]


def test_every_shape_lies_within_the_contour_bbox():
    x0, y0, w, h = g.CONTOUR_BBOX
    for e in g.IRISES + g.SHINES:
        assert x0 <= e["cx"] - e["rx"] and e["cx"] + e["rx"] <= x0 + w
        assert y0 <= e["cy"] - e["ry"] and e["cy"] + e["ry"] <= y0 + h


def test_path_is_closed_and_has_no_leftover_transform():
    assert g.CONTOUR_PATH.startswith("M")
    assert g.CONTOUR_PATH.endswith("z")
    assert "matrix" not in g.CONTOUR_PATH
