"""Conjugate at a finite point: multiplying by sqrt(x)+2 turns the root into
x-4, which then cancels against the denominator."""
import math

from common.limit_kit import LimitScene


class Lesson(LimitScene):
    lesson_id = "rationalization_conjugate_finite"

    def construct(self):
        self.check("(sqrt(x) - 2)/(x - 4)", 4, "1/4")
        self.hole_story(
            problem=r"\lim_{x \to 4} \frac{\sqrt{x} - 2}{x - 4}",
            substitution=[r"\frac{\sqrt{4} - 2}{4 - 4}", r"= \frac{0}{0}"],
            f=lambda x: (math.sqrt(x) - 2) / (x - 4), a=4, L=0.25,
            x_range=[0, 9, 1], y_range=[0, 0.6, 0.1], x_numbers=[2, 4, 6, 8],
            plot_range=[0.0, 9.0], h_start=2.5,
            algebra=[
                ("conjugate", [r"\frac{\sqrt{x} - 2}{x - 4} \cdot \frac{\sqrt{x} + 2}{\sqrt{x} + 2}",
                               r"= \frac{x - 4}{(x - 4)(\sqrt{x} + 2)}"]),
                ("cancel", [r"= \frac{1}{\sqrt{x} + 2}"]),
            ],
            simplified=lambda x: 1 / (math.sqrt(x) + 2),
            answer=r"\lim_{x \to 4} \frac{\sqrt{x} - 2}{x - 4} = \frac{1}{2 + 2} = \frac{1}{4}",
            L_label=r"\frac{1}{4}",
        )
