"""Pure value-transform helpers shared by several correction operations."""

from __future__ import annotations

import ast
import operator

import numpy as np

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_ALLOWED_COMPARE = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}

_ALLOWED_NP_FUNCS = frozenset(
    {
        "abs",
        "sqrt",
        "log",
        "log10",
        "log2",
        "exp",
        "sin",
        "cos",
        "tan",
        "arcsin",
        "arccos",
        "arctan",
        "sinh",
        "cosh",
        "tanh",
        "clip",
        "round",
        "floor",
        "ceil",
        "sign",
        "minimum",
        "maximum",
        "mean",
        "median",
        "std",
        "median",
        "nanmean",
        "nanmedian",
        "nanstd",
        "where",
        "isnan",
        "nan_to_num",
    }
)


class _SafeExpressionError(ValueError):
    pass


def _eval_ast(node: ast.AST, x: np.ndarray):
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body, x)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise _SafeExpressionError("Only numeric literals are allowed.")
    if isinstance(node, ast.Name):
        if node.id == "x":
            return x
        raise _SafeExpressionError(f"Unknown name: {node.id!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_eval_ast(node.left, x), _eval_ast(node.right, x))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_ast(node.operand, x))
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _ALLOWED_COMPARE:
        left = _eval_ast(node.left, x)
        right = _eval_ast(node.comparators[0], x)
        return _ALLOWED_COMPARE[type(node.ops[0])](left, right)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name):
            raise _SafeExpressionError("Only np.<function>(...) calls are allowed.")
        if node.func.value.id != "np" or node.func.attr not in _ALLOWED_NP_FUNCS:
            raise _SafeExpressionError(f"Function not allowed: {node.func.attr!r}")
        if node.keywords:
            raise _SafeExpressionError("Keyword arguments are not allowed.")
        args = [_eval_ast(arg, x) for arg in node.args]
        return getattr(np, node.func.attr)(*args)
    raise _SafeExpressionError(f"Expression element not allowed: {type(node).__name__}")


def op_delete(indices: np.ndarray) -> np.ndarray:
    return np.full(indices.shape, np.nan, dtype=np.float64)


def op_replace(indices: np.ndarray, value: float) -> np.ndarray:
    return np.full(indices.shape, float(value), dtype=np.float64)


def op_offset(values: np.ndarray, indices: np.ndarray, amount: float) -> np.ndarray:
    return values[indices] + float(amount)


def op_multiply(values: np.ndarray, indices: np.ndarray, factor: float) -> np.ndarray:
    return values[indices] * float(factor)


def op_expression(values: np.ndarray, indices: np.ndarray, expr: str) -> np.ndarray:
    """Evaluate ``expr`` with ``x`` bound to the selected values.

    The expression is parsed into an AST and evaluated by a restricted
    interpreter (see ``_eval_ast``) that only permits numeric literals, the
    ``x`` name, arithmetic/comparison operators, conditional expressions, and
    calls to a fixed whitelist of ``np.<function>`` calls. No attribute
    access, subscripting, name lookup beyond ``x``, or builtins are
    reachable, so this is safe to evaluate on expressions coming from an
    untrusted or shared session/history file, not just typed interactively.
    """

    x = values[indices]
    try:
        tree = ast.parse(expr, mode="eval")
        result = _eval_ast(tree, x)
    except _SafeExpressionError as exc:
        raise ValueError(f"Invalid expression: {exc}") from exc
    except SyntaxError as exc:
        raise ValueError(f"Invalid expression: {exc}") from exc
    return np.broadcast_to(np.asarray(result, dtype=np.float64), x.shape).copy()


def apply_action(values: np.ndarray, indices: np.ndarray, action: str, params: dict) -> np.ndarray:
    """Dispatch to the right transform based on an ``action`` parameter.

    Shared by :class:`ThresholdCorrection` and any future composite
    operation that lets the user pick "what to do" with a set of points.
    """

    if action == "delete":
        return op_delete(indices)
    if action == "replace":
        return op_replace(indices, params["replace_value"])
    if action == "offset":
        return op_offset(values, indices, params["offset_amount"])
    if action == "multiply":
        return op_multiply(values, indices, params["factor"])
    if action == "expression":
        return op_expression(values, indices, params["expr"])
    raise ValueError(f"Unknown action: {action}")


ACTION_CHOICES = [
    ("delete", "Delete (NaN)"),
    ("replace", "Replace with a value"),
    ("offset", "Offset (+/-)"),
    ("multiply", "Multiply by"),
    ("expression", "Custom expression"),
]
