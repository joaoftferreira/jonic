"""The "shoot Eggman" briefing: a few seconds of cartoon that tells the
children what they are supposed to do.

A kid with a Nerf blaster slides into one eye, Eggman's Egg Mobile slides into
the other, the kid fires, Eggman blows up, and the kid cheers. Then the eyes go
back to normal. It plays from the top on every press, because it is an
instruction rather than a mood.

The two actors stand on the same centres the emeralds use: those were searched
against the traced outline for the levellest, most mirrored pair that clears
the eye, which is exactly what two characters facing each other want.
"""
from eyes.emeralds import EYE_CENTERS

#: Kid on the left, Eggman on the right, so the shot travels the way the
#: children read.
KID_CENTER = EYE_CENTERS[0]
EGGMAN_CENTER = EYE_CENTERS[1]

#: The artwork is drawn in a 100-unit-tall box centred on its own origin, so
#: this is the whole character height in eye units. The eye gives us about 40
#: to play with before the outline clips a head off.
ACTOR_SCALE = 0.42

#: How far off its own centre each actor starts, in eye units. Comfortably past
#: the contour, so they slide in from off the face rather than fading up.
ENTRANCE_OFFSET = 90.0

#: Where the dart starts and ends, relative to each actor's centre. The muzzle
#: sits high on the kid's right; Eggman takes it in the head.
MUZZLE_OFFSET = (13.0, -2.0)
IMPACT_OFFSET = (-6.0, -9.0)

#: The dart is drawn about 19 units long; at full size it dwarfs the kid.
DART_SCALE = 0.45

#: How far the dart's flight sags below a straight line, at its midpoint.
#:
#: A straight shot between the two eyes crosses the notch that divides them,
#: where there is no white and the clip hides the dart for over half its
#: flight. That reads as a bug. Below y = -103 the two lobes join into one
#: continuous white area, so lobbing the dart through there keeps it visible
#: the whole way -- and a toy dart arcing is more believable than a laser.
DART_SAG = 19.0


def dart_point(u: float):
    """Where the dart is at u in 0..1 along its flight."""
    x0 = KID_CENTER[0] + MUZZLE_OFFSET[0]
    y0 = KID_CENTER[1] + MUZZLE_OFFSET[1]
    x1 = EGGMAN_CENTER[0] + IMPACT_OFFSET[0]
    y1 = EGGMAN_CENTER[1] + IMPACT_OFFSET[1]
    x = x0 + (x1 - x0) * u
    y = y0 + (y1 - y0) * u + DART_SAG * 4 * u * (1 - u)
    return x, y

# --- timing ---------------------------------------------------------------
ENTER_MS = 700       # both actors slide in
AIM_MS = 450         # a beat to read the scene before anything happens
SHOT_MS = 260        # the dart's flight
BOOM_MS = 700        # the explosion expanding and fading
CHEER_MS = 900       # the kid celebrating
EXIT_MS = 450        # everyone leaves and the eyes come back


def timeline() -> dict:
    """Start time of each beat, in ms from the button press."""
    enter = 0
    shot = enter + ENTER_MS + AIM_MS
    boom = shot + SHOT_MS
    cheer = boom + BOOM_MS
    exit_ = cheer + CHEER_MS
    return {
        "enter": enter,
        "shot": shot,
        "boom": boom,
        "cheer": cheer,
        "exit": exit_,
        "end": exit_ + EXIT_MS,
    }


def total_ms() -> int:
    return timeline()["end"]
