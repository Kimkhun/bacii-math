#!/usr/bin/env python3
"""
Verify BAC II limits exam questions in data/bacii-exam/limits/*.json.

For each question:
  1. Parse prompt_latex, compute the limit with SymPy, compare to answer_latex.
  2. Parse formula_latex (when it's an "LHS = RHS" identity used as the stated
     technique/formula) and verify LHS - RHS simplifies to 0 with SymPy, or that
     a "-> value" claim matches the SymPy limit of that sub-expression.

Prints a per-question PASS/FAIL/SKIP report and a summary.
"""
import glob
import json
import re
import sys

import sympy as sp
from sympy.parsing.latex import parse_latex

x = sp.symbols("x")


_PI_SYMBOL = sp.Symbol("pi")


def to_sympy(latex_str):
    """Parse a LaTeX string to a SymPy expression, with light cleanup.

    parse_latex turns \\pi into a plain Symbol('pi') rather than the sp.pi
    constant, which silently breaks sp.limit substitution — fix that up.
    """
    s = latex_str.strip()
    # \sqrt3 (no braces) silently truncates parsing in antlr's latex grammar;
    # \sqrt{3} works fine.
    s = re.sub(r"\\sqrt(\d)", r"\\sqrt{\1}", s)
    expr = parse_latex(s)
    if _PI_SYMBOL in expr.free_symbols:
        expr = expr.subs(_PI_SYMBOL, sp.pi)
    e_symbol = sp.Symbol("e")
    if e_symbol in expr.free_symbols:
        expr = expr.subs(e_symbol, sp.E)
    return expr


def find_group(s, open_idx):
    """s[open_idx] must be '{'. Return (content, index_after_closing_brace)."""
    assert s[open_idx] == "{"
    depth = 0
    for i in range(open_idx, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[open_idx + 1:i], i + 1
    raise ValueError("unbalanced braces")


def split_top_level(s, seps):
    """Split s on any of the single-char separators in `seps`, but only at
    brace-depth 0 (so separators inside {...} groups are preserved)."""
    parts = []
    depth = 0
    buf = []
    for ch in s:
        if ch == "{":
            depth += 1
            buf.append(ch)
        elif ch == "}":
            depth -= 1
            buf.append(ch)
        elif ch in seps and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def to_point(point_latex):
    point_latex = point_latex.strip()
    if point_latex in (r"+\infty", r"\infty"):
        return sp.oo
    if point_latex == r"-\infty":
        return -sp.oo
    return to_sympy(point_latex)


def extract_lim(latex_str):
    """Find first \\lim_{x\\to POINT} in latex_str (brace-aware). Returns
    (point_latex, rest_of_string_after_the_lim_block, match_end_index) or None."""
    m = re.search(r"\\lim_\{", latex_str)
    if not m:
        return None
    open_idx = m.end() - 1
    content, close_idx = find_group(latex_str, open_idx)
    mm = re.match(r"x\s*\\to\s*(.+)", content)
    if not mm:
        return None
    return mm.group(1), latex_str[:m.start()], latex_str[close_idx:], close_idx


def compute_limit(prompt_latex):
    """Extract the \\lim_{x\\to POINT} EXPR structure and evaluate with SymPy."""
    found = extract_lim(prompt_latex.strip())
    if not found:
        return None, "could not parse \\lim_{x\\to ...} structure"
    point_latex, _, expr_latex, _ = found
    expr_latex = expr_latex.strip()

    try:
        point = to_point(point_latex)
    except Exception as e:
        return None, f"could not parse limit point '{point_latex}': {e}"

    try:
        expr = to_sympy(expr_latex)
    except Exception as e:
        return None, f"could not parse expression '{expr_latex}': {e}"

    try:
        val = sp.limit(expr, x, point)
    except Exception as e:
        return None, f"sympy.limit failed: {e}"

    return val, None


def values_equal(a, b):
    if a in (sp.oo, -sp.oo, sp.zoo) or b in (sp.oo, -sp.oo, sp.zoo):
        return a == b
    try:
        diff = sp.simplify(sp.nsimplify(a) - sp.nsimplify(b))
        return diff == 0
    except Exception:
        try:
            return abs(complex(a) - complex(b)) < 1e-9
        except Exception:
            return False


GENERIC_MARKERS = (r"\text", r"\dots", "a_n", "b_n")


def check_piece(piece, subs_map=None):
    """Check a single ';'-or-\\quad-separated claim. Returns (ok_or_None, detail)."""
    subs_map = subs_map or {}
    piece = piece.strip()
    if piece.startswith(r"\quad"):
        piece = piece[len(r"\quad"):].strip()
    if piece.startswith(r"\ "):
        piece = piece[2:].strip()
    if not piece:
        return None, "empty"

    if any(marker in piece for marker in GENERIC_MARKERS):
        return None, f"skipped (generic theorem statement): {piece}"

    # substitution definition, e.g. "t=x-\frac{\pi}{3}" or "X=\frac{1}{x}\to0"
    if re.match(r"^\\?\s*[a-zA-Z]\s*=", piece) and "\\lim" not in piece:
        return None, f"skipped (variable substitution, true by definition): {piece}"

    lim = extract_lim(piece)
    if lim:
        point_latex, prefix, rest, _ = lim
        if "=" not in rest:
            return None, f"skipped (unparseable lim claim): {piece}"
        expr_latex, rhs_latex = rest.split("=", 1)
        try:
            point = to_point(point_latex)
            expr = to_sympy(expr_latex.strip())
            rhs = to_sympy(rhs_latex.strip())
            val = sp.limit(expr, x, point)
            ok = values_equal(val, rhs)
            return ok, f"lim[x->{point_latex.strip()}] {expr_latex.strip()} = {val} (claimed {rhs_latex.strip()})"
        except Exception as e:
            return None, f"skipped (error evaluating lim claim '{piece}': {e})"

    if r"\xrightarrow" in piece:
        m = re.search(r"\\xrightarrow\[(.+?)\]\{[^}]*\}", piece)
        if not m:
            return None, f"skipped (unparseable arrow): {piece}"
        sub = m.group(1)  # e.g. "x\to\infty"
        mm = re.match(r"x\s*\\to\s*(.+)", sub)
        if not mm:
            return None, f"skipped (unparseable arrow target): {piece}"
        point_latex = mm.group(1)
        lhs_latex = piece[:m.start()].strip()
        rhs_latex = piece[m.end():].strip()
        try:
            point = to_point(point_latex)
            lhs = to_sympy(lhs_latex)
            rhs = to_sympy(rhs_latex) if rhs_latex else sp.Integer(0)
            val = sp.limit(lhs, x, point)
            ok = values_equal(val, rhs)
            return ok, f"lim[x->{point_latex}] {lhs_latex} = {val} (claimed {rhs_latex or '0'})"
        except Exception as e:
            return None, f"skipped (error evaluating arrow claim '{piece}': {e})"

    if "=" in piece:
        lhs_latex, rhs_latex = piece.split("=", 1)
        try:
            lhs = to_sympy(lhs_latex.strip())
            rhs = to_sympy(rhs_latex.strip())
            for sym_name, repl in subs_map.items():
                sym = sp.Symbol(sym_name)
                if sym in lhs.free_symbols:
                    lhs = lhs.subs(sym, repl)
                if sym in rhs.free_symbols:
                    rhs = rhs.subs(sym, repl)
            diff = sp.simplify(sp.expand(lhs - rhs))
            ok = diff == 0
            return ok, f"{lhs_latex.strip()} - ({rhs_latex.strip()}) simplifies to {diff}"
        except Exception as e:
            return None, f"skipped (error evaluating identity '{piece}': {e})"

    return None, f"skipped (no '=' or lim/arrow found): {piece}"


def check_formula(formula_latex):
    """
    formula_latex may contain multiple ';'-separated claims (algebraic identities,
    explicit \\lim{...}=... claims, or \\xrightarrow[...]{} limit claims). Generic
    theorem statements (continuity, squeeze, ratio-of-leading-terms with symbolic
    coefficients, etc.) and variable substitutions are skipped, not failed, since
    SymPy can't check a claim about an arbitrary/symbolic function.
    Returns (ok: bool|None, detail: str).
    """
    pieces = split_top_level(formula_latex, [";", ","])

    subs_map = {}
    for piece in pieces:
        m = re.match(r"^\\?\s*([a-zA-Z])\s*=\s*(.+)$", piece.strip())
        if m and "\\lim" not in piece:
            var, expr_latex = m.groups()
            expr_latex = re.split(r"\\to", expr_latex)[0].strip()  # drop trailing "\to 0" etc.
            try:
                subs_map[var] = to_sympy(expr_latex)
            except Exception:
                pass

    results = [check_piece(p, subs_map) for p in pieces]

    hard_results = [r for r in results if r[0] is not None]
    if not hard_results:
        return None, "; ".join(r[1] for r in results)
    ok = all(r[0] for r in hard_results)
    return ok, "; ".join(r[1] for r in results)


def main():
    files = sorted(glob.glob("data/bacii-exam/limits/*.json"))
    if not files:
        files = sorted(glob.glob("/home/lavid/bacii-math/data/bacii-exam/limits/*.json"))

    total = 0
    answer_pass = answer_fail = answer_skip = 0
    formula_pass = formula_fail = formula_skip = 0

    for fpath in files:
        data = json.load(open(fpath))
        year = data["exams"][0]["exam_date"][:4]
        for exam in data["exams"]:
            for sec in exam["sections"]:
                for q in sec["questions"]:
                    total += 1
                    label = f"{year}{q['label']}"
                    prompt = q["prompt_latex"]
                    answer = q["answer_latex"]
                    formula = q.get("formula_latex", "")

                    val, err = compute_limit(prompt)
                    if err:
                        answer_skip += 1
                        print(f"[{label}] ANSWER SKIP  prompt='{prompt}'  ({err})")
                    else:
                        try:
                            expected = to_point(answer)
                        except Exception as e:
                            answer_skip += 1
                            print(f"[{label}] ANSWER SKIP  could not parse answer '{answer}': {e}")
                        else:
                            ok = values_equal(val, expected)
                            if ok:
                                answer_pass += 1
                                print(f"[{label}] ANSWER PASS  sympy={val}  expected={answer}")
                            else:
                                answer_fail += 1
                                print(f"[{label}] ANSWER FAIL  sympy={val}  expected={answer}  prompt='{prompt}'")

                    if not formula:
                        formula_skip += 1
                        continue
                    fok, fdetail = check_formula(formula)
                    if fok is None:
                        formula_skip += 1
                        print(f"[{label}] FORMULA SKIP  {fdetail}")
                    elif fok:
                        formula_pass += 1
                        print(f"[{label}] FORMULA PASS  {fdetail}")
                    else:
                        formula_fail += 1
                        print(f"[{label}] FORMULA FAIL  {fdetail}")

    print()
    print(f"Total questions: {total}")
    print(f"Answers:  {answer_pass} pass, {answer_fail} fail, {answer_skip} skip")
    print(f"Formulas: {formula_pass} pass, {formula_fail} fail, {formula_skip} skip")

    if answer_fail or formula_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
