"""Generic slot-template filling, shared by the ``limit`` and ``integral``
topic generators (and the integral structure registry's sample builder).
``{v}`` is replaced with the variable name; ``{a}``..``{n}`` are replaced from
fixed coefficient pools. All pool values are positive — sign variety comes
from the template structure itself."""
_COEFF_POOLS = {
    "a": ["3", "5", "2", "4", "7", "6"],
    "b": ["2", "4", "6", "3", "8", "1", "5"],
    "c": ["4", "5", "1", "7", "9", "2", "3"],
    "d": ["2", "5", "1", "3", "7", "6", "4"],
    "f": ["1/2", "3/4", "2/3", "1/3", "5/2", "1/4"],
    "g": ["2", "4", "6", "3", "1", "5"],
    "s": ["2", "3", "4"],
    "k": ["2", "3", "4", "5"],
    "n": ["2", "3", "4"],
}

_SLOT_NAMES = tuple(_COEFF_POOLS)


def _fill(rng, tpl, var):
    func = tpl.replace("{v}", var)
    for slot, choices in _COEFF_POOLS.items():
        func = func.replace("{" + slot + "}", rng.choice(choices))
    return func


def _slots_in(tpl):
    return {c for c in _SLOT_NAMES if "{" + c + "}" in tpl}


def fill_structured(rng, tpl, var):
    """Fill a slot template, remembering the chosen values (slot order in the
    template) so dependent bound strings can reuse the exact same numbers."""
    expr = tpl.replace("{v}", var)
    vals = {}
    for slot in _SLOT_NAMES:
        if "{" + slot + "}" not in expr:
            continue
        val = rng.choice(_COEFF_POOLS[slot])
        vals[slot] = val
        expr = expr.replace("{" + slot + "}", val)
    return expr, vals


def fill_bound(rng, bound, var, vals):
    """Fill a bound string reusing already-chosen slot values; leftover slots
    (not present in the integrand template) get fresh values."""
    s = bound.replace("{v}", var)
    for slot, val in vals.items():
        s = s.replace("{" + slot + "}", val)
    for slot in _SLOT_NAMES:
        if "{" + slot + "}" in s:
            s = s.replace("{" + slot + "}", rng.choice(_COEFF_POOLS[slot]))
    return s
