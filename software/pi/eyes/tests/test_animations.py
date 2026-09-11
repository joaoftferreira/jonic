import pytest

from eyes import animations as a
from eyes.tests import outline


def test_the_three_requested_animations_exist_plus_a_way_back_to_center():
    assert set(a.ANIMATIONS) == {"blink", "look_left", "look_right", "center"}


def test_blink_is_quick_but_drawable_on_a_slow_panel():
    assert 400 <= a.ANIMATIONS["blink"]["duration_ms"] <= 700


def test_the_lid_holds_shut_long_enough_to_be_painted():
    """A single instantaneous closure is never drawn on a panel that drops
    frames, and the blink then looks like it stalls halfway down."""
    assert 0 < a.BLINK_CLOSED_FROM < a.BLINK_CLOSED_TO < 1
    hold_ms = (a.BLINK_CLOSED_TO - a.BLINK_CLOSED_FROM) * a.BLINK_MS
    # Two frames at the ~15 fps the Pi 3 manages, so one always lands inside.
    assert hold_ms >= 2 * (1000 / 15)


def test_gaze_animations_move_opposite_ways_and_center_does_not_move():
    assert a.ANIMATIONS["look_left"]["gaze"] == -1
    assert a.ANIMATIONS["look_right"]["gaze"] == 1
    assert a.ANIMATIONS["center"]["gaze"] == 0


def test_the_inner_eye_moves_less_than_the_outer_one():
    assert 0 < a.GAZE_INNER_RATIO < 1


def test_at_full_gaze_the_outer_iris_stays_whole():
    """The eye moving away from the notch has room; it should lose nothing."""
    from eyes import geometry as g

    rest = [outline.visible_fraction(iris) for iris in g.IRISES]
    # left eye looking left, right eye looking right
    assert outline.visible_fraction(g.IRISES[0], -a.GAZE_TRAVEL) >= rest[0] - 0.01
    assert outline.visible_fraction(g.IRISES[1], +a.GAZE_TRAVEL) >= rest[1] - 0.01


def test_at_full_gaze_the_inner_eye_keeps_its_iris_and_its_shine():
    """This is the constraint that sets GAZE_INNER_RATIO. A straight equal
    shift buries the inner iris in the notch and erases its shine, which reads
    as a rendering fault rather than as a glance."""
    from eyes import geometry as g

    inner = a.GAZE_TRAVEL * a.GAZE_INNER_RATIO
    # right eye while looking left, left eye while looking right
    for iris, shine, direction in ((g.IRISES[1], g.SHINES[1], -1),
                                   (g.IRISES[0], g.SHINES[0], +1)):
        assert outline.visible_fraction(iris, direction * inner) > 0.65
        assert outline.visible_fraction(shine, direction * inner) > 0.45


def test_the_outer_eye_moves_far_enough_to_read_across_a_room():
    """The panel is 1024x600 and the contour spans its full width, so a unit of
    travel is about 7.2 px. Anything under ~64 px is not a visible glance."""
    from eyes import geometry as g

    PANEL_WIDTH = 1024                      # measured on the MPI7010 7" panel
    pixels_per_unit = PANEL_WIDTH / g.CONTOUR_BBOX[2]
    assert a.GAZE_TRAVEL * pixels_per_unit > 64


def test_lid_color_is_a_sonic_blue_hex():
    assert a.LID_COLOR.startswith("#") and len(a.LID_COLOR) == 7
    r, gr, b = (int(a.LID_COLOR[i:i + 2], 16) for i in (1, 3, 5))
    assert b > r and b > gr, "the eyelid should read as blue"


@pytest.mark.parametrize("name", ["blink", "look_left", "look_right", "center"])
def test_known_names_validate(name):
    assert a.is_animation(name)


@pytest.mark.parametrize("name", ["", "BLINK", "look_up", "; drop table"])
def test_unknown_names_are_rejected(name):
    assert not a.is_animation(name)
