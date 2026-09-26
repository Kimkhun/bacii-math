"""Transition deduction rules for Limit exercises.

Given the previous expression (or initial problem expression) and the student's
current expression, deduce which Bac II formula was applied to transition between them.

Strictly uses approved Bac II formula tags from formulas.json:
- trig_half_angle: រូបមន្តកន្លះមុំ និងបញ្ចុះដឺក្រេ
- trig_double_angle: រូបមន្តមុំទ្វេត្រីកោណមាត្រ
- trig_fundamental_relations: ទំនាក់ទំនងសំខាន់ៗ / រូបមន្តគ្រឹះត្រីកោណមាត្រ
- trig_sum_to_product: រូបមន្តបំប្លែងផលបូកទៅជាផលគុណ
- limit_sin_x_over_x: រូបមន្តលីមីតត្រីកោណមាត្រគ្រឹះ
- factoring_0_0: ដាក់ជាផលគុណកត្តារាងមិនកំណត់ 0/0
- cancel_common_factor: សម្រួលកត្តារួម
- rationalization_conjugate_finite: គុណកន្សោមឆ្លាស់បំបាត់រ៉ាឌីកាល់
- direct_substitution: ជំនួសតម្លៃផ្ទាល់
- unclassified_valid: ជំហានត្រឹមត្រូវ (មិនទាន់បញ្ជាក់រូបមន្ត)
"""
from sympy import (
    Symbol,
    Wild,
    cancel,
    cos,
    degree,
    diff,
    expand,
    factor,
    fraction,
    gcd,
    limit,
    oo,
    simplify,
    sin,
    sqrt,
    tan,
    sympify,
    S,
)


def _is_equivalent(a, b, var=None):
    """Check if two expressions are algebraically equivalent."""
    try:
        if a == b:
            return True
        diff_val = simplify(a - b)
        if diff_val == 0 or diff_val == S.Zero:
            return True
    except Exception:
        pass
    return False


def _preserves_limit(prev, curr, var, point, target_val=None):
    """Verify mathematical truth: does curr preserve the same limit at point as prev/target_val?"""
    try:
        if target_val is not None:
            curr_lim = limit(curr, var, point)
            if _is_equivalent(curr_lim, target_val):
                return True
        if prev is not None:
            prev_lim = limit(prev, var, point)
            curr_lim = limit(curr, var, point)
            return _is_equivalent(prev_lim, curr_lim)
    except Exception:
        pass
    return False


def _check_direct_substitution(curr, var, point, target_val=None):
    """Check if curr is the final evaluated numeric constant matching the limit."""
    try:
        if not curr.free_symbols or var not in curr.free_symbols:
            if target_val is not None and _is_equivalent(curr, target_val):
                return True
    except Exception:
        pass
    return False


def _check_cancel_common_factor(prev, curr):
    """Check if curr is genuinely obtained by cancelling common factors from prev."""
    try:
        if _is_equivalent(prev, curr):
            p_num, p_den = fraction(prev)
            c_num, c_den = fraction(curr)
            common = gcd(p_num, p_den)
            # Genuine cancellation requires a non-trivial common factor to be eliminated
            if common != 1 and common != S.One and common != -1:
                cancelled = cancel(prev)
                if _is_equivalent(cancelled, curr) and cancelled != prev:
                    return True
            if p_den != c_den and cancel(prev) == curr and cancel(prev) != prev:
                return True
    except Exception:
        pass
    return False


def _check_factoring_0_0(prev, curr, var, point):
    """Check if curr is the factored form of prev (polynomials factored to reveal roots)."""
    try:
        p_num, p_den = fraction(prev)
        c_num, c_den = fraction(curr)

        f_num = factor(p_num)
        f_den = factor(p_den)
        if (f_num != p_num or f_den != p_den):
            if _is_equivalent(f_num / f_den, curr) or (_is_equivalent(f_num, c_num) and _is_equivalent(f_den, c_den)):
                return True
    except Exception:
        pass
    return False


def _check_trig_half_angle(prev, curr, var):
    """Check half-angle / power reduction: 1 - cos(w) <=> 2*sin(w/2)^2.
    Strict structural signature:
    - prev contained cos(w)
    - curr introduces sin(w/2) or cos(w/2) where argument is halved (w -> w/2)
    - expressions are algebraically equivalent.
    """
    try:
        if not _is_equivalent(prev, curr, var):
            return False

        prev_cos_args = {t.args[0] for t in prev.atoms(cos) if t.args}
        curr_sin_args = {t.args[0] for t in curr.atoms(sin) if t.args}
        curr_cos_args = {t.args[0] for t in curr.atoms(cos) if t.args}

        # Halved argument introduced in sine (from 1 - cos(w) -> 2 sin^2(w/2))
        has_half_sine = any(
            any(_is_equivalent(c_arg, p_arg / 2, var) for p_arg in prev_cos_args)
            for c_arg in curr_sin_args
        )
        if has_half_sine:
            return True

        # Halved argument introduced in cosine (from 1 + cos(w) -> 2 cos^2(w/2))
        has_half_cos = any(
            any(_is_equivalent(c_arg, p_arg / 2, var) for p_arg in prev_cos_args)
            for c_arg in curr_cos_args
        )
        if has_half_cos:
            return True

        # Wild replacement check for 1 - cos(w)
        w_a = Wild("w_a")
        rep1 = prev.replace(1 - cos(w_a), lambda w_a: 2 * sin(w_a / 2) ** 2)
        if rep1 != prev and _is_equivalent(rep1, curr, var):
            if any(_is_equivalent(c_arg, p_arg / 2, var) for p_arg in prev_cos_args for c_arg in curr_sin_args):
                return True
    except Exception:
        pass
    return False


def _check_trig_double_angle(prev, curr, var):
    """Check double-angle identities: sin(2w) <=> 2*sin(w)*cos(w) or cos(2w) expansions.
    Strict structural signature:
    - Expansion: prev has sin(2w) and curr has BOTH sin(w) AND cos(w) at halved argument!
      or prev has cos(2w) and curr has cos^2(w) - sin^2(w).
    - Compression: prev has sin(w)*cos(w) and curr has sin(2w).
    """
    try:
        if not _is_equivalent(prev, curr, var):
            return False

        prev_sin_args = {t.args[0] for t in prev.atoms(sin) if t.args}
        prev_cos_args = {t.args[0] for t in prev.atoms(cos) if t.args}
        curr_sin_args = {t.args[0] for t in curr.atoms(sin) if t.args}
        curr_cos_args = {t.args[0] for t in curr.atoms(cos) if t.args}

        # Expansion sin(2w) -> 2 sin(w) cos(w): curr must have both sin(w) and cos(w) where prev had sin(2w)
        for p_arg in prev_sin_args:
            for c_arg in curr_sin_args:
                if _is_equivalent(p_arg, 2 * c_arg, var):
                    # Check that curr also carries cos at this same halved argument c_arg
                    if any(_is_equivalent(c_arg, c_cos_arg, var) for c_cos_arg in curr_cos_args):
                        return True

        # Compression 2 sin(w) cos(w) -> sin(2w): curr has sin(2w) while prev had both sin(w) and cos(w)
        for c_arg in curr_sin_args:
            for p_arg in prev_sin_args:
                if _is_equivalent(c_arg, 2 * p_arg, var):
                    if any(_is_equivalent(p_arg, p_cos_arg, var) for p_cos_arg in prev_cos_args):
                        return True
    except Exception:
        pass
    return False


def _check_trig_fundamental_relations(prev, curr, var):
    """Check Pythagorean identity sin^2(w) + cos^2(w) = 1.
    Strict structural signature:
    - Argument w is strictly invariant (no halving, no doubling: prev_args == curr_args).
    - One trig power converted to another (sin^2 <-> 1 - cos^2).
    """
    try:
        if not _is_equivalent(prev, curr, var):
            return False

        prev_args = {t.args[0] for t in prev.atoms(sin, cos) if t.args}
        curr_args = {t.args[0] for t in curr.atoms(sin, cos) if t.args}

        if prev_args and curr_args and prev_args == curr_args:
            p_sins = len(prev.atoms(sin))
            c_sins = len(curr.atoms(sin))
            p_cos = len(prev.atoms(cos))
            c_cos = len(curr.atoms(cos))
            if (p_sins != c_sins or p_cos != c_cos):
                return True
    except Exception:
        pass
    return False


def _check_sinc_standard_limit(prev, curr, var, point):
    """Check standard trigonometric limit sin(kx)/(kx) -> 1 or isolating sinc form.
    Strict structural signature:
    - Case A: sine factors evaluated away using the limit (count of sin decreases while limit preserved).
    - Case B: reorganization to isolate sin(u)/u with power of variable in denominator.
    """
    if point != 0 and point != S.Zero:
        return False
    try:
        p_sins = prev.atoms(sin)
        c_sins = curr.atoms(sin)

        # 1. Sine factor was evaluated to 1 by applying the limit
        if len(p_sins) > len(c_sins) and _preserves_limit(prev, curr, var, point):
            return True

        # 2. Expression reorganized into standard sinc form (sin(u)/u)
        # Arguments of sines are preserved, but numerator/denominator grouped with u
        if c_sins and _preserves_limit(prev, curr, var, point):
            p_num, p_den = fraction(prev)
            c_num, c_den = fraction(curr)
            # If denominator has variable and sine arguments match
            p_args = {t.args[0] for t in p_sins if t.args}
            c_args = {t.args[0] for t in c_sins if t.args}
            if p_args and p_args == c_args and var in c_den.free_symbols:
                return True
    except Exception:
        pass
    return False


def _check_radical_conjugate(prev, curr, var):
    """Check conjugate rationalization for radical expressions."""
    try:
        p_sqrts = prev.atoms(sqrt) or [a for a in prev.atoms() if hasattr(a, "is_Pow") and a.exp == S.Half]
        if p_sqrts:
            p_num, p_den = fraction(prev)
            c_num, c_den = fraction(curr)
            p_num_sq = p_num.atoms(sqrt) or [a for a in p_num.atoms() if hasattr(a, "is_Pow") and a.exp == S.Half]
            c_num_sq = c_num.atoms(sqrt) or [a for a in c_num.atoms() if hasattr(a, "is_Pow") and a.exp == S.Half]
            p_den_sq = p_den.atoms(sqrt) or [a for a in p_den.atoms() if hasattr(a, "is_Pow") and a.exp == S.Half]
            c_den_sq = c_den.atoms(sqrt) or [a for a in c_den.atoms() if hasattr(a, "is_Pow") and a.exp == S.Half]

            if (p_num_sq and not c_num_sq) or (p_den_sq and not c_den_sq):
                if _is_equivalent(prev, curr, var) or _preserves_limit(prev, curr, var, None):
                    return True
    except Exception:
        pass
    return False


def _check_limit_power_identity(prev, curr, var, point):
    """Check if curr is dividing by (x - point) or using power derivative quotient."""
    try:
        p_num, p_den = fraction(prev)
        deg_p = max(degree(p_num, var) if (hasattr(p_num, "is_polynomial") and p_num.is_polynomial(var)) else 0,
                    degree(p_den, var) if (hasattr(p_den, "is_polynomial") and p_den.is_polynomial(var)) else 0)
        if deg_p > 6:
            d_p = diff(p_num, var).subs(var, point) / diff(p_den, var).subs(var, point)
            if _is_equivalent(curr, d_p):
                return True
            divided = (p_num / (var - point)) / (p_den / (var - point))
            if _is_equivalent(curr, divided, var):
                return True
    except Exception:
        pass
    return False


def _check_euler_steps(prev, curr, var):
    """Check if curr is base - 1 or exponent * (base - 1) from prev = base**pwr."""
    try:
        if hasattr(prev, "is_Pow") and prev.is_Pow:
            base, pwr = prev.as_base_exp()
            if _is_equivalent(curr, base - 1, var):
                return "euler_base_minus_one", "base minus one"
            if _is_equivalent(curr, pwr * (base - 1), var):
                return "euler_exponent_limit", "exponent limit product"
    except Exception:
        pass
    return None


def deduce_limit_step(prev_expr, curr_expr, var_sym, limit_point, target_val=None):
    """Deduce which Bac II formula transformed prev_expr into curr_expr.

    Collects all matching signatures to support compound steps (e.g. identity + cancel)
    and strictly avoids guessing false-positive formula tags.
    """
    if curr_expr is None:
        return None

    # 1. Direct substitution / evaluation to final constant value
    if _check_direct_substitution(curr_expr, var_sym, limit_point, target_val):
        return {
            "formula": "direct_substitution",
            "label": "direct substitution to final value",
            "compound_formulas": ["direct_substitution"],
        }

    if prev_expr is None:
        return None

    # Euler steps (base deviation f(x)-1 or product g(x)(f(x)-1))
    euler_match = _check_euler_steps(prev_expr, curr_expr, var_sym)
    if euler_match:
        f_tag, f_label = euler_match
        return {
            "formula": f_tag,
            "label": f_label,
            "compound_formulas": [f_tag],
        }

    # Verify mathematical correctness: does curr_expr preserve the limit or identity?
    if not _is_equivalent(prev_expr, curr_expr, var_sym) and not _preserves_limit(prev_expr, curr_expr, var_sym, limit_point, target_val):
        return None

    matches = []

    # Power limit identity for high-degree rational forms (priority 11)
    if _check_limit_power_identity(prev_expr, curr_expr, var_sym, limit_point):
        matches.append({"formula": "limit_power_identity", "label": "power difference limit identity", "priority": 11})

    # Domain-specific trigonometric identities (priority 10)
    if _check_trig_half_angle(prev_expr, curr_expr, var_sym):
        matches.append({"formula": "trig_half_angle", "label": "half-angle identity", "priority": 10})

    if _check_trig_double_angle(prev_expr, curr_expr, var_sym):
        matches.append({"formula": "trig_double_angle", "label": "double-angle identity", "priority": 10})

    if _check_trig_fundamental_relations(prev_expr, curr_expr, var_sym):
        matches.append({"formula": "trig_fundamental_relations", "label": "fundamental trig identity", "priority": 9})

    if _check_radical_conjugate(prev_expr, curr_expr, var_sym):
        matches.append({"formula": "rationalization_conjugate_finite", "label": "conjugate rationalization", "priority": 9})

    if _check_sinc_standard_limit(prev_expr, curr_expr, var_sym, limit_point):
        matches.append({"formula": "limit_sin_x_over_x", "label": "standard sinc limit", "priority": 8})

    if _check_factoring_0_0(prev_expr, curr_expr, var_sym, limit_point):
        matches.append({"formula": "factoring_0_0", "label": "factored form", "priority": 7})

    if _check_cancel_common_factor(prev_expr, curr_expr):
        matches.append({"formula": "cancel_common_factor", "label": "cancelled form", "priority": 6})

    if matches:
        matches.sort(key=lambda m: m["priority"], reverse=True)
        primary = matches[0]
        return {
            "formula": primary["formula"],
            "label": primary["label"],
            "compound_formulas": [m["formula"] for m in matches],
        }

    # Generic algebraic equivalent rewrite with no specific identified formula
    if _is_equivalent(prev_expr, curr_expr, var_sym):
        return {
            "formula": "unclassified_valid",
            "label": "valid, formula not identified",
            "compound_formulas": ["unclassified_valid"],
        }

    return None
