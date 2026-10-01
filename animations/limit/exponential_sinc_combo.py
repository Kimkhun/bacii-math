"""Exponential + sin(x)/x: split into two pieces with known limits."""
import math

from common.limit_kit import LimitScene


class Lesson(LimitScene):
    lesson_id = "exponential_sinc_combo"

    def construct(self):
        self.check("(exp(x) + exp(-x))*sin(3*x)**2/(2*x**2)", 0, 9)
        self.hole_story(
            problem=r"\lim_{x \to 0} \frac{(e^x + e^{-x})\sin^2(3x)}{2x^2}",
            substitution=[r"\frac{(1 + 1)\sin^2 0}{2 \cdot 0^2}", r"= \frac{0}{0}"],
            f=lambda x: (math.exp(x) + math.exp(-x)) * math.sin(3 * x) ** 2 / (2 * x * x), a=0, L=9,
            x_range=[-1.5, 1.5, 0.5], y_range=[0, 10, 1], x_numbers=[-1, 1], y_numbers=[5],
            h_start=1.0,
            algebra=[
                ("split", [r"= \frac{e^x + e^{-x}}{2} \cdot \left(\frac{\sin 3x}{x}\right)^2"]),
                ("pieces", [r"\xrightarrow[x \to 0]{} \frac{1 + 1}{2} \cdot 3^2"]),
            ],
            answer=r"\lim_{x \to 0} \frac{(e^x + e^{-x})\sin^2(3x)}{2x^2} = 9",
            L_label="9",
        )
