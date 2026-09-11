"""The seven-and-two Chaos Emeralds that fill each eye.

Nine gems per eye: eight on the corners of an octagon and the blue one in the
middle. They snake in from the outer edge of each eye, loop inward around the
centre until the octagon closes, the blue one zooms in from behind, and the
ring then turns slowly forever.

The centres and the radius are not guesses. Each eye lobe was measured for the
largest circle that fits entirely inside the contour, and the ring is sized to
sit inside that with room for a gem. test_emeralds re-checks it against the
real outline, so re-running the geometry extractor on edited art cannot quietly
push the gems outside the eye.
"""

# Where each eye's octagon is centred. Not the largest circle that fits in each
# lobe -- those sit at different heights, and the two clusters then read as
# lopsided. These are the levellest, most mirrored pair of centres that still
# clear the outline: identical height, and the same distance either side of the
# notch between the eyes. Both were searched against the traced contour.
EYE_CENTERS = ((-176.4, -113.9), (-93.3, -113.9))

#: Clearance both centres are known to have. The ring plus a gem must fit here.
LOBE_RADIUS = 20.4

RING_RADIUS = 15.0        # distance from the centre to each octagon corner
GEM_SCALE = 0.72          # the gem art is ~10 x 13.5 units at scale 1
CENTER_GEM_SCALE = 0.85
GEM_HALF_HEIGHT = 6.75    # half the gem art's height, before scaling

# Where the snake comes in from, per eye, in degrees. Mirrored: the left eye's
# gems fly in from the far left, the right eye's from the far right, so the two
# trails sweep inward toward the nose.
ENTRY_ANGLES = (180.0, 0.0)
ENTRY_RADIUS = 55.0       # well outside the lobe, so they start off-screen

# Eight ring colours in octagon order. Ordered by hue so neighbours blend as
# the ring turns, rather than clashing.
RING_COLORS = (
    ("green", "#00C853"),
    ("cyan", "#00E5FF"),
    ("lila", "#9B51E0"),
    ("pink", "#FF3FD0"),
    ("rosa", "#FF85B3"),
    ("red", "#FF1E1E"),
    ("orange", "#FF8A00"),
    ("yellow", "#FFE000"),
)
CENTER_COLOR = ("blue", "#2979FF")

# Timing. Every gem flies the same trail at the same speed, one stagger apart,
# which is what makes it read as a snake rather than a fan: the first gem in
# has been travelling longest when the formation closes, so it ends up furthest
# around the ring, and the last one barely gets past the entry point.
FLY_MS = 600              # off-screen to the edge of the ring, a straight run
ORBIT_MS = 1400           # the leading gem's time going around the centre
STAGGER_MS = 120          # gap between gems
CENTER_MS = 600           # the blue gem's zoom in from behind
SPIN_MS = 24000           # one full turn of the finished octagon

#: Angular speed of the orbit. Fixed by the stagger: gems one stagger apart
#: must end up exactly one octagon corner apart, so this is not free.
DEG_PER_MS = 360.0 / 8 / STAGGER_MS

ENTRY_MS = FLY_MS + ORBIT_MS      # all gems land together, at this moment

CORNER_STEP_DEG = 360.0 / 8


def gem_sweep_deg(index: int) -> float:
    """Degrees gem `index` travels around the centre before it stops.

    The leading gem (0) sweeps furthest; each later one stops a corner short."""
    orbit_ms = ENTRY_MS - index * STAGGER_MS - FLY_MS
    return orbit_ms * DEG_PER_MS


def settle_ms() -> int:
    """How long until the octagon is formed and turning."""
    return ENTRY_MS + CENTER_MS


def ring_slots():
    """(name, colour, corner angle in degrees) for each octagon corner."""
    return [(name, color, i * CORNER_STEP_DEG)
            for i, (name, color) in enumerate(RING_COLORS)]
