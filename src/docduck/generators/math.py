"""Procedural LaTeX equation generator.

Generates unique equations every time by randomly combining mathematical
constructs with random coefficients, variables, and nesting.

All output is raw LaTeX (no $ delimiters) compatible with matplotlib mathtext.
"""

import random

from ..defaults import DEFAULTS as D

_LATIN_VARS = list("xyzabcnmktpqrsuvw")
_GREEK_VARS = [
    r"\alpha",
    r"\beta",
    r"\gamma",
    r"\delta",
    r"\epsilon",
    r"\theta",
    r"\lambda",
    r"\mu",
    r"\sigma",
    r"\tau",
    r"\phi",
    r"\psi",
    r"\omega",
    r"\rho",
    r"\nu",
    r"\xi",
    r"\eta",
]
_FUNCS = [r"\sin", r"\cos", r"\tan", r"\log", r"\ln", r"\exp"]
_RELATIONS = ["=", r"\leq", r"\geq", r"\approx", r"\equiv", r"\neq", r"\sim"]
_BIN_OPS = ["+", "-", r"\cdot", r"\times"]


def _var():
    """Random variable (Latin or Greek)."""
    if random.random() < 0.3:
        return random.choice(_GREEK_VARS) + " "
    return random.choice(_LATIN_VARS)


def _coeff():
    """Random coefficient string (may be empty)."""
    r = random.random()
    if r < 0.3:
        return ""
    if r < 0.7:
        return str(random.randint(*D["math"]["coeff_int_range"]))
    return f"{random.uniform(*D['math']['coeff_float_range']):.1f}"


def _int(lo=0, hi=20):
    return str(random.randint(lo, hi))


def _subscript(base=None):
    if base is None:
        base = _var()
    sub = random.choice([_int(0, 9), _var(), f"{_var()},{_var()}"])
    return f"{base}_{{{sub}}}"


def _superscript(base=None):
    if base is None:
        base = _var()
    exp = random.choice([_int(2, 5), _var(), f"{_var()}+{_int(1, 3)}"])
    return f"{base}^{{{exp}}}"


def _term(depth=0):
    """Generate a random mathematical term."""
    if depth > 3:
        return _var()
    r = random.random()
    if r < 0.15:
        return _coeff() + _var()
    if r < 0.3:
        return _superscript(_var())
    if r < 0.4:
        return _subscript(_var())
    if r < 0.5:
        f = random.choice(_FUNCS)
        return f"{f}({_var()})"
    if r < 0.6:
        return f"\\frac{{{_term(depth + 1)}}}{{{_term(depth + 1)}}}"
    if r < 0.7:
        return f"\\sqrt{{{_term(depth + 1)}}}"
    if r < 0.8:
        return f"\\left({_term(depth + 1)} {random.choice(_BIN_OPS)} {_term(depth + 1)}\\right)"
    return _coeff() + _superscript(_var())


def _expression(n_terms=None, depth=0):
    """Generate a sum/product of terms."""
    if n_terms is None:
        n_terms = random.randint(3, 6)
    parts = [_term(depth)]
    for _ in range(n_terms - 1):
        op = random.choice(["+", "-", "+", "+"])
        parts.append(f"{op} {_term(depth)}")
    return " ".join(parts)


def gen_polynomial():
    """e.g. 3x^4 + 7x^3 - 2x^2 + 5x - 12 = 0"""
    v = random.choice(_LATIN_VARS[:4])
    deg = random.randint(*D["math"]["polynomial_degree_range"])
    terms = []
    for i in range(deg, 0, -1):
        c = random.randint(1, 15)
        if i == deg:
            terms.append(f"{c}{v}^{{{i}}}" if i > 1 else f"{c}{v}")
        else:
            sign = random.choice(["+", "-"])
            terms.append(f"{sign} {c}{v}^{{{i}}}" if i > 1 else f"{sign} {c}{v}")
    c0 = random.randint(1, 30)
    terms.append(f"{random.choice(['+', '-'])} {c0}")
    return " ".join(terms) + " = 0"


def gen_fraction_equation():
    """e.g. \\frac{2x^2 + 3x + 1}{x^2 - 1} = \\frac{5x + 2}{2x - 3}"""
    v = _var()
    rel = random.choice(["=", r"\leq", r"\geq"])
    lhs_num = f"{_coeff()}{v}^{{{_int(2, 3)}}} + {_coeff()}{v} + {_int(1, 9)}"
    lhs_den = f"{v}^{{{_int(1, 2)}}} - {_int(1, 9)}"
    rhs_num = f"{_coeff()}{v} + {_int(1, 9)}"
    rhs_den = f"{_int(1, 5)}{v} - {_int(1, 9)}"
    return f"\\frac{{{lhs_num}}}{{{lhs_den}}} {rel} \\frac{{{rhs_num}}}{{{rhs_den}}}"


def gen_integral():
    """e.g. \\int_0^{\\pi} \\sin(x) \\, dx"""
    v = random.choice(["x", "t", "u", r"\theta"])
    dv = f"d{v}" if len(v) == 1 else "d\\theta"
    integrand_choices = [
        f"{random.choice(_FUNCS)}({v}) \\cdot {random.choice(_FUNCS)}({v})",
        f"{v}^{{{random.randint(2, 5)}}} \\cdot e^{{{random.choice(['-', ''])}{_coeff()}{v}}}",
        f"e^{{{random.choice(['-', ''])}{v}}} \\cdot {random.choice(_FUNCS)}({_coeff()}{v})",
        f"\\frac{{{_coeff()}{v}^{{{_int(2, 4)}}}}}{{{v}^{{{_int(1, 3)}}} + {_int(1, 5)}}} + {_term(1)}",
        f"{_coeff()}{v}^{{{_int(2, 4)}}} \\cdot {random.choice(_FUNCS)}({v}) + {_term(1)}",
        f"\\frac{{{random.choice(_FUNCS)}({v})}}{{{_term(1)}}} \\cdot {_term(1)}",
        f"\\left({_term(1)} + {_term(1)}\\right) \\cdot {random.choice(_FUNCS)}({v})",
    ]
    integrand = random.choice(integrand_choices)

    bound_choices = [
        ("0", "1"),
        ("0", r"\infty"),
        ("-\\infty", "\\infty"),
        ("0", r"\pi"),
        ("a", "b"),
        ("0", "T"),
        (_int(0, 5), _int(6, 20)),
    ]
    lo, hi = random.choice(bound_choices)

    if random.random() < 0.4:
        # Definite with result
        return f"\\int_{{{lo}}}^{{{hi}}} {integrand} \\, {dv} = {_term()}"
    return f"\\int_{{{lo}}}^{{{hi}}} {integrand} \\, {dv}"


def gen_summation():
    """e.g. \\sum_{i=1}^{n} i^2 = \\frac{n(n+1)(2n+1)}{6}"""
    idx = random.choice(["i", "j", "k", "n"])
    upper = random.choice(["n", "N", r"\infty", _int(5, 100)])
    lower_val = random.choice(["0", "1"])

    body_choices = [
        f"\\frac{{{idx}^{{{_int(2, 4)}}}}}{{{_int(1, 5)} + {idx}^{{{_int(1, 2)}}}}}",
        f"\\frac{{{_coeff()}}}{{{idx}^{{{_int(1, 3)}}}}} \\cdot {_term(1)}",
        f"(-1)^{{{idx}}} \\frac{{{_term(1)}}}{{{idx}! \\cdot {_int(1, 5)}^{{{idx}}}}}",
        f"{_var()}_{{{idx}}} \\cdot {_var()}_{{{idx}}}^{{{_int(2, 3)}}}",
        f"\\frac{{{random.choice(_FUNCS)}({idx} \\cdot {_var()})}}{{{idx}^{{{_int(1, 3)}}} + {_int(1, 9)}}}",
        f"\\left(\\frac{{{_var()}_{{{idx}}}}}{{{_var()}_{{{idx}}} + {_int(1, 5)}}}\\right)^{{{_int(2, 3)}}}",
    ]
    body = random.choice(body_choices)

    eq = f"\\sum_{{{idx}={lower_val}}}^{{{upper}}} {body}"
    if random.random() < 0.4:
        eq += f" = {_term()}"
    return eq


def gen_product():
    """e.g. \\prod_{i=1}^{n} x_i"""
    idx = random.choice(["i", "j", "k"])
    upper = random.choice(["n", "N", _int(3, 10)])
    body = random.choice(
        [
            f"{_var()}_{{{idx}}}",
            f"\\left(1 + \\frac{{{_int(1, 5)}}}{{{idx}}}\\right)",
            f"\\frac{{{idx}}}{{{idx} + {_int(1, 5)}}}",
        ]
    )
    return f"\\prod_{{{idx}=1}}^{{{upper}}} {body}"


def gen_limit():
    """e.g. \\lim_{x \\to 0} \\frac{\\sin(x)}{x} = 1"""
    v = random.choice(["x", "n", "t", "h"])
    target = random.choice(["0", r"\infty", "-\\infty", "a", _int(1, 5)])
    body_choices = [
        f"\\frac{{\\sin({v})}}{{{v}}}",
        f"\\frac{{{v}^{{{_int(2, 3)}}} - {_int(1, 9)}}}{{{v} - {_int(1, 5)}}}",
        f"\\left(1 + \\frac{{{_int(1, 5)}}}{{{v}}}\\right)^{{{v}}}",
        f"\\frac{{{random.choice(_FUNCS)}({v})}}{{{v}}}",
    ]
    body = random.choice(body_choices)
    eq = f"\\lim_{{{v} \\to {target}}} {body}"
    if random.random() < 0.5:
        eq += f" = {_int(0, 10)}"
    return eq


def gen_derivative():
    """e.g. \\frac{d}{dx} [x^3 + 2x] = 3x^2 + 2"""
    v = random.choice(["x", "t", "r", r"\theta"])
    dv = v if len(v) == 1 else "\\theta"
    body = _expression(random.randint(2, 3))
    style = random.choice(["leibniz", "partial", "prime"])
    if style == "leibniz":
        return f"\\frac{{d}}{{d{dv}}} \\left[{body}\\right]"
    elif style == "partial":
        f_name = random.choice(["f", "g", "u", "v", r"\phi", r"\psi"])
        return f"\\frac{{\\partial {f_name}}}{{\\partial {dv}}} = {_term()}"
    else:
        f_name = random.choice(["f", "g", "y"])
        return f"{f_name}'({v}) = {_expression(2)}"


def _matrix_entry(depth=0):
    """Random matrix cell: small integer most of the time, occasional
    variable / fraction / expression for structural variety."""
    r = random.random()
    if r < 0.55:
        return str(random.randint(-9, 9))
    if r < 0.75:
        return _var()
    if r < 0.88:
        return f"{random.randint(1, 9)}{_var()}"
    if r < 0.95:
        lo, hi = sorted([random.randint(1, 8), random.randint(1, 8)])
        return f"\\frac{{{lo}}}{{{hi}}}"
    # cos/sin cell (common in rotation / covariance matrices).
    # Always wrap the arg in parens so ``\sinx`` (invalid) can't be emitted
    # when the arg is a plain letter.
    arg = random.choice(["\\theta", "\\alpha", "x", "\\phi"])
    return f"\\{random.choice(['cos', 'sin'])}({arg})"


def _matrix(rows, cols, env="pmatrix", depth=0):
    """Emit a LaTeX matrix literal in ``env`` (``pmatrix``, ``bmatrix``, ``vmatrix``)."""
    rows_tex = " \\\\ ".join(
        " & ".join(_matrix_entry(depth + 1) for _ in range(cols)) for _ in range(rows)
    )
    return f"\\begin{{{env}}} {rows_tex} \\end{{{env}}}"


def _vector(n, env="pmatrix"):
    return _matrix(n, 1, env=env)


def gen_matrix_literal():
    """A standalone matrix or a named matrix equality like A = [[...]]."""
    rows, cols = random.choice([(2, 2), (2, 2), (3, 3), (2, 3), (3, 2), (3, 4), (4, 3)])
    env = random.choice(["pmatrix", "bmatrix"])
    name = random.choice(["A", "B", "M", "P", "Q", "R", "X"])
    if random.random() < 0.7:
        return f"{name} = {_matrix(rows, cols, env=env)}"
    return _matrix(rows, cols, env=env)


def gen_matrix_vector_product():
    """``Ax = b`` with concrete entries: exercises block tables of mixed dims."""
    rows = random.choice([2, 2, 3, 3, 4])
    cols = random.choice([rows, rows - 1, rows + 1])
    cols = max(cols, 2)
    env = random.choice(["pmatrix", "bmatrix"])
    A = _matrix(rows, cols, env=env)
    x = _vector(cols, env=env)
    b = _vector(rows, env=env)
    return f"{A} {x} = {b}"


def gen_matrix_determinant():
    """Determinant with actual entries and its expansion: mixes pmatrix + vmatrix."""
    if random.random() < 0.5:
        # 2×2 explicit
        a, b = _matrix_entry(), _matrix_entry()
        c, d = _matrix_entry(), _matrix_entry()
        return (
            f"\\det\\begin{{bmatrix}} {a} & {b} \\\\ {c} & {d} \\end{{bmatrix}}"
            f" = ({a})({d}) - ({b})({c})"
        )
    # 3×3 symbolic expansion
    return (
        "\\det(A) = \\sum_{i=1}^{n} (-1)^{i+1} a_{1i} M_{1i}"
        if random.random() < 0.5
        else (
            "\\begin{vmatrix} a_{11} & a_{12} \\\\ a_{21} & a_{22} \\end{vmatrix}"
            " = a_{11} a_{22} - a_{12} a_{21}"
        )
    )


def gen_eigen_equation():
    """Concrete eigenvalue equation ``A v = λ v`` with entries."""
    a, b = _matrix_entry(), _matrix_entry()
    c, d = _matrix_entry(), _matrix_entry()
    x1, x2 = _var(), _var()
    lam = random.choice([r"\lambda", r"\lambda_1", r"\mu"])
    return (
        f"\\begin{{bmatrix}} {a} & {b} \\\\ {c} & {d} \\end{{bmatrix}}"
        f" \\begin{{bmatrix}} {x1} \\\\ {x2} \\end{{bmatrix}}"
        f" = {lam} \\begin{{bmatrix}} {x1} \\\\ {x2} \\end{{bmatrix}}"
    )


def gen_matrix_equation():
    """Mix of symbolic matrix statements and concrete-entry matrix layouts."""
    choices = [
        # Symbolic (single-line, no env): keeps the old variety
        lambda: f"\\det(A) = {_var()}{_var()} - {_var()}{_var()}",
        lambda: f"A{_var()} = {random.choice(_GREEK_VARS)} {_var()}",
        lambda: f"\\|{_var()}\\| = \\sqrt{{{_expression(2)}}}",
        lambda: f"\\hat{{{_var()}}} = \\frac{{{_var()}}}{{\\|{_var()}\\|}}",
        lambda: "A^{-1} = \\frac{1}{\\det(A)} \\mathrm{adj}(A)",
        # Concrete matrix layouts (wrap with amsmath envs; pdflatex path handles
        # these; matplotlib mathtext fallback will stringify them as-is)
        gen_matrix_literal,
        gen_matrix_literal,
        gen_matrix_vector_product,
        gen_matrix_determinant,
        gen_eigen_equation,
    ]
    return random.choice(choices)()


def gen_trig_identity():
    """e.g. \\sin^2(x) + \\cos^2(x) = 1"""
    v = random.choice(["x", r"\theta", r"\alpha", r"\phi"])
    identities = [
        f"\\sin^2({v}) + \\cos^2({v}) = 1",
        f"\\tan({v}) = \\frac{{\\sin({v})}}{{\\cos({v})}}",
        f"\\sin(2{v}) = 2\\sin({v})\\cos({v})",
        f"\\cos(2{v}) = \\cos^2({v}) - \\sin^2({v})",
        f"e^{{i{v}}} = \\cos({v}) + i\\sin({v})",
        f"\\sin({v} + {_var()}) = \\sin({v})\\cos({_var()}) + \\cos({v})\\sin({_var()})",
    ]
    return random.choice(identities)


def gen_probability():
    """e.g. P(A \\cap B) = P(A) P(B|A)"""
    events = random.sample(list("ABCXYZ"), 2)
    a, b = events
    formulas = [
        f"P({a} \\cap {b}) = P({a}) P({b}|{a})",
        f"P({a} \\cup {b}) = P({a}) + P({b}) - P({a} \\cap {b})",
        f"P({a}|{b}) = \\frac{{P({b}|{a}) P({a})}}{{P({b})}}",
        f"\\mathrm{{Var}}({a}) = E[{a}^2] - (E[{a}])^2",
        f"E[{a}] = \\sum_{{{_var()}}} {_var()} \\cdot P({a} = {_var()})",
        f"\\sigma_{{{a}}} = \\sqrt{{\\frac{{1}}{{{_var()}}} \\sum_{{{random.choice(['i', 'j'])}=1}}^{{{_var()}}} ({_var()}_{{{random.choice(['i', 'j'])}}}-\\bar{{{_var()}}})^2}}",
    ]
    return random.choice(formulas)


def gen_physics():
    """Random physics-style equation."""
    choice = random.randint(0, 5)
    if choice == 0:
        return f"F = {_coeff()}\\frac{{{_var()}{_var()}}}{{{_var()}^2}} + {_term(1)} - \\frac{{{_term(1)}}}{{{_var()}^3}}"
    elif choice == 1:
        return f"E = \\frac{{{_int(1, 5)}}}{{{_int(1, 3)}}} {_var()} {_var()}^2 + {_term(1)} \\cdot {random.choice(_FUNCS)}({_var()})"
    elif choice == 2:
        return f"\\Delta {_var()} = {_var()}_0 {_var()} + \\frac{{{_int(1, 3)}}}{{{_int(1, 3)}}} {_var()} {_var()}^2 + {_term(1)}"
    elif choice == 3:
        return f"\\vec{{F}} = {_var()} \\frac{{d\\vec{{{_var()}}}}}{{d{_var()}}} + {_term(1)} \\times \\vec{{{_var()}}}"
    elif choice == 4:
        field = random.choice(["\\phi", "\\psi", "V"])
        source = random.choice(["\\rho", "q"])
        perm = random.choice(["\\epsilon_0", "\\epsilon"])
        return f"\\nabla^2 {field} = -{_coeff()}\\frac{{{source}}}{{{perm}}} + \\frac{{\\partial^2 {field}}}{{\\partial {_var()}^2}}"
    else:
        return f"\\frac{{\\partial {_var()}}}{{\\partial {_var()}}} + {_var()} \\cdot \\nabla {_var()} = {_term(1)} + \\frac{{{_term(1)}}}{{{_term(1)}}}"


def gen_set_theory():
    """e.g. A \\cup B = B \\cup A"""
    sets = random.sample(list("ABCXYZ"), 3)
    a, b, c = sets
    formulas = [
        f"{a} \\cup ({b} \\cap {c}) = ({a} \\cup {b}) \\cap ({a} \\cup {c})",
        f"|{a} \\cup {b}| = |{a}| + |{b}| - |{a} \\cap {b}|",
        f"{a} \\cap {b}^c = {a} \\cap {b}^c",
        f"{a} \\subset {b} \\Rightarrow {a} \\cap {b} = {a}",
    ]
    return random.choice(formulas)


def gen_general_equation():
    """General equation: expr = expr."""
    lhs = _expression(random.randint(3, 5))
    rhs = _expression(random.randint(2, 4))
    rel = random.choice(_RELATIONS)
    return f"{lhs} {rel} {rhs}"


# All single-line generators
GENERATORS = [
    gen_polynomial,
    gen_fraction_equation,
    gen_integral,
    gen_summation,
    gen_product,
    gen_limit,
    gen_derivative,
    gen_matrix_equation,
    gen_trig_identity,
    gen_probability,
    gen_physics,
    gen_set_theory,
    gen_general_equation,
]


def gen_equation() -> str:
    """Generate a random single-line LaTeX equation."""
    gen = random.choice(GENERATORS)
    return gen()


def gen_equation_multiline() -> list[str]:
    """Generate a random multi-line equation (list of LaTeX strings)."""
    style = random.choice(["system", "derivation", "cases"])

    if style == "system":
        n = random.randint(3, 5)
        return [gen_general_equation() for _ in range(n)]
    elif style == "derivation":
        # Chain of equalities: a = b = c = d
        v = _var()
        lines = [f"{v} = {_expression(3)}"]
        for _ in range(random.randint(2, 4)):
            lines.append(f"= {_expression(random.randint(2, 4))}")
        return lines
    else:  # cases
        v = _var()
        n = random.randint(2, 4)
        _case_rels = [">", "<", "=", "\\geq", "\\leq"]
        rel = random.choice(_case_rels)
        lines = [f"{v} = {_term()} \\mathrm{{\\quad if\\quad}} {_var()} {rel} {_int(0, 10)}"]
        for _ in range(n - 1):
            rel = random.choice(_case_rels)
            lines.append(f"= {_term()} \\mathrm{{\\quad if\\quad}} {_var()} {rel} {_int(0, 10)}")
        return lines
