import math

from eyes import emeralds as e
from eyes.tests import outline


def test_nine_gems_per_eye_with_blue_in_the_middle():
    assert len(e.RING_COLORS) == 8
    assert e.CENTER_COLOR[0] == "blue"


def test_the_nine_colours_are_the_ones_asked_for():
    names = {n for n, _ in e.RING_COLORS} | {e.CENTER_COLOR[0]}
    assert names == {"green", "cyan", "blue", "lila", "pink",
                     "rosa", "yellow", "orange", "red"}


def test_every_colour_is_distinct_and_a_hex_value():
    colors = [c for _, c in e.RING_COLORS] + [e.CENTER_COLOR[1]]
    assert len(set(colors)) == len(colors)
    assert all(len(c) == 7 and c.startswith("#") for c in colors)


def test_the_eight_corners_are_evenly_spaced_around_a_full_turn():
    angles = [a for _, _, a in e.ring_slots()]
    assert angles == [0, 45, 90, 135, 180, 225, 270, 315]


def test_the_ring_plus_a_gem_fits_inside_the_measured_lobe():
    reach = e.RING_RADIUS + e.GEM_HALF_HEIGHT * e.GEM_SCALE
    assert reach < e.LOBE_RADIUS, f"gems reach {reach:.1f}, lobe is {e.LOBE_RADIUS}"


def test_the_centre_gem_does_not_touch_the_ring():
    centre_reach = e.GEM_HALF_HEIGHT * e.CENTER_GEM_SCALE
    ring_inner = e.RING_RADIUS - e.GEM_HALF_HEIGHT * e.GEM_SCALE
    assert centre_reach < ring_inner


def test_every_gem_lands_inside_the_real_eye_outline():
    """The decisive check: each corner, in each eye, against the traced art."""
    reach = e.GEM_HALF_HEIGHT * e.GEM_SCALE
    for cx, cy in e.EYE_CENTERS:
        for _, _, angle in e.ring_slots():
            a = math.radians(angle)
            gx = cx + e.RING_RADIUS * math.cos(a)
            gy = cy + e.RING_RADIUS * math.sin(a)
            for k in range(12):           # sample the gem's own outline
                t = 2 * math.pi * k / 12
                assert outline.inside_contour(gx + reach * math.cos(t),
                                              gy + reach * math.sin(t)), \
                    f"gem at {angle}deg escapes the eye at ({cx}, {cy})"


def test_the_gems_start_outside_the_eye_so_they_fly_in():
    assert e.ENTRY_RADIUS > e.LOBE_RADIUS + e.GEM_HALF_HEIGHT


def test_the_two_eyes_enter_from_opposite_sides():
    assert e.ENTRY_ANGLES == (180.0, 0.0)


def test_the_reveal_settles_in_about_three_seconds():
    assert 2500 <= e.settle_ms() <= 3500


def test_the_finished_octagon_turns_slowly():
    assert e.SPIN_MS >= 12000
