"""Differential-equations topic: solve an ODE from curated BAC II exercises.
``solver.py`` computes the answer; ``generator.py`` replays curated exercises
from ``data/curated/curated.json``; ``data/formulas.json`` supplies the
formula-sheet catalog entries for this topic. ``grader.py`` has no custom
rule beyond the generic core (the ODE arbitrary-constant symbols ``C1``/``C2``
are handled by ``engine.core.grading``'s parser locals).
"""
