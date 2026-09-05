"""Complex-number topic: modulus, argument, conjugate, real/imaginary parts,
arithmetic, powers, De Moivre, and nth roots. One module per exercise
technique (mirrors the curated data layout in ``data/curated/{formula_name}.json``):

  modulus.py         |z| = sqrt(a^2+b^2)
  argument.py        arg(z) via atan2
  conjugate.py       z̄ = a - bi
  real_imaginary.py  Re(z) / Im(z)
  arithmetic.py      z1 (+|-|*|/) z2
  power.py           z^n, small n, direct algebraic expansion
  de_moivre.py       z^n, large n, via trigonometric form + De Moivre
  nth_roots.py       one n-th root of z (reverse-built from a clean root)
  trig.py            shared "nice special angle" helpers for de_moivre/nth_roots

``solver.py`` is the technique dispatcher; ``generator.py`` builds problems
(templates + the curated-textbook pool + the Gemini-proposed variant);
``grader.py`` has no custom rule (this topic's one special case — numeric
argument-angle closeness — lives inline in ``engine.core.grading``).
"""
