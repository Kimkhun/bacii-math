"""Differential-equations topic: solve a linear ODE with constant
coefficients and initial conditions. ``structures.py`` is the template
registry (every question is sampled from one of its structures; the textbook
BAC II exercises are instances of them); ``generator.py`` samples it;
``solver.py`` computes the answer with dsolve and takes the graded steps from
the template's blueprint (``blueprint_spec.py`` + ``data/blueprints.json``);
``data/formulas.json`` supplies the formula-sheet catalog entries for this
topic. ``grader.py`` has no custom rule beyond the generic core (the ODE
arbitrary-constant symbols ``C1``/``C2`` are handled by
``engine.core.grading``'s parser locals, and a general-solution step accepts
the student's own constant names).
"""
