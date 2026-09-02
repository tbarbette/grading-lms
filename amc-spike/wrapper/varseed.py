"""Safe, seed-reproducible evaluation of per-question numeric variables.

Only a whitelisted AST subset is evaluated (no arbitrary eval): numeric
literals, +-*/// %, **, unary +/-, references to earlier-resolved variables,
and a single randint(lo, hi) builtin driven by a seeded RNG so the same seed
always yields the same values (needed for "vary numbers year to year").
"""

import ast
import operator
import random

import jinja2

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class VariableError(ValueError):
    pass


def _safe_eval(expr: str, names: dict, rng: random.Random):
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return _BINOPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
            return _UNARYOPS[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.Name):
            if node.id in names:
                return names[node.id]
            raise VariableError(f"Unknown variable: {node.id}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "randint" and len(node.args) == 2:
                lo, hi = _eval(node.args[0]), _eval(node.args[1])
                return rng.randint(int(lo), int(hi))
            raise VariableError(f"Unsupported function: {node.func.id}")
        raise VariableError(f"Unsupported expression near: {ast.dump(node)}")

    tree = ast.parse(expr, mode="eval")
    return _eval(tree)


def eval_variables(variables: dict[str, str], seed: int) -> dict:
    rng = random.Random(seed)
    resolved: dict[str, object] = {}
    for name, expr in variables.items():
        resolved[name] = _safe_eval(str(expr).strip(), resolved, rng)
    return resolved


def render_source(template_text: str, variables: dict[str, str], seed: int):
    values = eval_variables(variables, seed)
    rendered = jinja2.Template(template_text).render(**values)
    return rendered, values


def parse_variables_form(raw: str) -> dict[str, str]:
    """Parse a textarea of `name = expression` lines (one per line)."""
    variables: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, expr = line.split("=", 1)
        variables[name.strip()] = expr.strip()
    return variables
