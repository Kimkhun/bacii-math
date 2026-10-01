"""House style for lesson animations: the 3Blue1Brown look, tuned for small screens.

Dark background, the classic 3b1b blue/yellow/teal accents, LaTeX math only.
Videos carry no prose (captions are rendered by the web under the video), so
there are no fonts to worry about beyond Computer Modern from LaTeX.
"""
from manim import (
    BLUE_C,
    GREEN_C,
    GREY_B,
    GREY_D,
    RED_C,
    TEAL_C,
    YELLOW_C,
    ManimColor,
)

BACKGROUND = ManimColor("#0e1116")

CURVE = BLUE_C          # the function being studied
CURVE_ALT = TEAL_C      # its simplified / rewritten form
POINT = YELLOW_C        # moving points, highlighted values
LIMIT = GREEN_C         # the limit value, boxed answers
WARN = RED_C            # indeterminate forms (0/0, ∞-∞, …)
AXIS = GREY_B
GRID = GREY_D

#: Math is drawn larger than Manim's default so it stays legible on a phone
#: (the video is usually shown ~360-700 px wide).
TEX_SCALE = 1.0
