"""Half-angle + sin(x)/x: 1 - cos(4x) = 2 sin^2(2x)."""
import math

from common.limit_kit import LimitScene


class Lesson(LimitScene):
    lesson_id = "half_angle_sinc_combo"

    def construct(self):
        self.check("(1 - cos(4*x))/x**2", 0, 8)
        self.hole_story(
            problem=r"\lim_{x \to 0} \frac{1 - \cos(4x)}{x^2}",
            substitution=[r"\frac{1 - \cos 0}{0^2}", r"= \frac{0}{0}"],
            f=lambda x: (1 - math.cos(4 * x)) / (x * x), a=0, L=8,
            x_range=[-1.5, 1.5, 0.5], y_range=[0, 9, 1], x_numbers=[-1, 1], y_numbers=[4],
            h_start=1.0,
            algebra=[
                ("identity", [r"\frac{1 - \cos(4x)}{x^2} = \frac{2\sin^2(2x)}{x^2}"]),
                ("square", [r"= 2\left(\frac{\sin 2x}{x}\right)^2", r"\xrightarrow[x \to 0]{} 2 \cdot 2^2"]),
            ],
            answer=r"\lim_{x \to 0} \frac{1 - \cos(4x)}{x^2} = 8",
            L_label="8",
        )
