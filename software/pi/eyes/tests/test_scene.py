from eyes import emeralds, scene
from eyes.tests import outline


def test_the_kid_is_on_the_left_and_eggman_on_the_right():
    assert scene.KID_CENTER[0] < scene.EGGMAN_CENTER[0]


def test_the_two_actors_stand_at_the_same_height():
    assert scene.KID_CENTER[1] == scene.EGGMAN_CENTER[1]


def test_the_actors_reuse_the_centres_already_proven_to_fit():
    assert {scene.KID_CENTER, scene.EGGMAN_CENTER} == set(emeralds.EYE_CENTERS)


def test_each_actor_fits_inside_its_own_eye():
    """Half the character height must clear the outline, or heads get clipped."""
    half = 100 * scene.ACTOR_SCALE / 2
    for cx, cy in (scene.KID_CENTER, scene.EGGMAN_CENTER):
        assert outline.inside_contour(cx, cy - half * 0.9)
        assert outline.inside_contour(cx, cy + half * 0.9)


def test_they_start_off_the_face_so_they_slide_in():
    x0, _, w, _ = __import__("eyes.geometry", fromlist=["x"]).CONTOUR_BBOX
    assert scene.KID_CENTER[0] - scene.ENTRANCE_OFFSET < x0
    assert scene.EGGMAN_CENTER[0] + scene.ENTRANCE_OFFSET > x0 + w


def test_the_beats_run_in_order_and_never_overlap():
    t = scene.timeline()
    order = ["enter", "shot", "boom", "cheer", "exit", "end"]
    times = [t[k] for k in order]
    assert times == sorted(times)
    assert len(set(times)) == len(times)


def test_the_whole_briefing_is_short_enough_to_hold_attention():
    assert 3000 <= scene.total_ms() <= 5000


def test_the_dart_flies_from_the_kid_toward_eggman():
    muzzle_x = scene.KID_CENTER[0] + scene.MUZZLE_OFFSET[0]
    impact_x = scene.EGGMAN_CENTER[0] + scene.IMPACT_OFFSET[0]
    assert muzzle_x < impact_x


def test_the_dart_stays_on_the_white_for_its_whole_flight():
    """A straight shot crosses the notch between the eyes, where the clip hides
    it for half the flight. The arc exists to avoid exactly that."""
    for k in range(41):
        x, y = scene.dart_point(k / 40)
        assert outline.inside_contour(x, y), f"dart leaves the eye at u={k/40:.2f}"


def test_the_dart_actually_arcs_rather_than_flying_straight():
    mid = scene.dart_point(0.5)
    straight = (scene.dart_point(0.0)[1] + scene.dart_point(1.0)[1]) / 2
    assert mid[1] > straight + 10        # +y is downward, so it sags


def test_the_dart_is_drawn_smaller_than_a_character():
    assert scene.DART_SCALE < 1
