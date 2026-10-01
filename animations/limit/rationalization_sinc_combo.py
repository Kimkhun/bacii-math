"""Conjugate + sin(x)/x: the conjugate leaves 2x on top, which pairs with
sin(2x) below."""
import math

from common.limit_kit import LimitScene


class Lesson(LimitScene):
    lesson_id = "rationalization_sinc_combo"

    def construct(self):
        self.check("(sqrt(1 + x) - sqrt(1 - x))/sin(2*x)", 0, "1/2")
        self.hole_story(
            problem=r"\lim_{x \to 0} \frac{\sqrt{1 + x} - \sqrt{1 - x}}{\sin(2x)}",
            substitution=[r"\frac{\sqrt{1} - \sqrt{1}}{\sin 0}", r"= \frac{0}{0}"],
            f=lambda x: (math.sqrt(1 + x) - math.sqrt(1 - x)) / math.sin(2 * x), a=0, L=0.5,
            x_range=[-1, 1, 0.5], y_range=[0, 1.5, 0.25],
            x_labels=[(-0.5, r"-\tfrac{1}{2}"), (0.5, r"\tfrac{1}{2}")],
            plot_range=[-0.95, 0.95], h_start=0.8,
            algebra=[
                ("conjugate", [r"= \frac{(1 + x) - (1 - x)}{\sin(2x)\left(\sqrt{1 + x} + \sqrt{1 - x}\right)}",
                               r"= \frac{2x}{\sin(2x)} \cdot \frac{1}{\sqrt{1 + x} + \sqrt{1 - x}}"]),
                ("split", [r"\xrightarrow[x \to 0]{} 1 \cdot \frac{1}{1 + 1}"]),
            ],
            answer=r"\lim_{x \to 0} \frac{\sqrt{1 + x} - \sqrt{1 - x}}{\sin(2x)} = \frac{1}{2}",
            L_label=r"\frac{1}{2}",
        )
