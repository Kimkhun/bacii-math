"""Integral topic: definite (polynomial, trig, linear_argument, u_substitution,
mixed_sum, by_parts) and indefinite (power, expand, split, linear_argument,
usub, trig_sec) variants. ``solver.py`` computes answers; ``generator.py``
builds live problems from parameterized templates; ``structures.py`` is the
admin-page structure registry mapping every one of the 124 curated BAC II
integral exercises to a template (``all_integral_structures`` /
``build_sample`` / ``build_pattern_latex`` / ``source_label_map``).
``grader.py`` has no custom rule (the "+C" indefinite-integral tolerance is a
one-line dispatch on ``question_type`` inline in ``engine.core.grading``).
"""
