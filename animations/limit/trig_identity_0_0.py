"""Pythagorean identity on a 0/0 form: cos^2 x = (1 - sin x)(1 + sin x)."""
import math

from common.limit_kit import LimitScene


class Lesson(LimitScene):
    lesson_id = "trig_identity_0_0"

    def construct(self):
        self.check("(1 - sin(x))/cos(x)**2", "pi/2", "1/2")
        self.hole_story(
            problem=r"\lim_{x \to \frac{\pi}{2}} \frac{1 - \sin x}{\cos^2 x}",
            substitution=[r"\frac{1 - \sin\frac{\pi}{2}}{\cos^2\frac{\pi}{2}}", r"= \frac{1 - 1}{0} = \frac{0}{0}"],
            f=lambda x: (1 - math.sin(x)) / math.cos(x) ** 2, a=math.pi / 2, L=0.5,
            x_range=[0, math.pi, math.pi / 4], y_range=[0, 1.2, 0.25],
            x_labels=[(math.pi / 2, r"\frac{\pi}{2}"), (math.pi, r"\pi")],
            plot_range=[0.0, math.pi], h_start=1.2, h_end=0.03,
            algebra=[
                ("identity", [r"\frac{1 - \sin x}{\cos^2 x} = \frac{1 - \sin x}{1 - \sin^2 x}",
                              r"= \frac{1 - \sin x}{(1 - \sin x)(1 + \sin x)}"]),
                ("cancel", [r"= \frac{1}{1 + \sin x}"]),
            ],
            simplified=lambda x: 1 / (1 + math.sin(x)),
            answer=r"\lim_{x \to \frac{\pi}{2}} \frac{1 - \sin x}{\cos^2 x} = \frac{1}{1 + 1} = \frac{1}{2}",
            L_label=r"\frac{1}{2}",
        )
