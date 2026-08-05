"""Pure value-transform helpers shared by several correction operations."""

from __future__ import annotations

import numpy as np


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

    Only ``x`` and the ``np`` module are exposed, builtins are stripped, and
    any expression containing ``__`` is rejected. This is meant as a
    convenience for a trusted, local, single-user tool - not a general
    purpose sandbox.
    """

    if "__" in expr:
        raise ValueError("Expression not allowed (double underscore forbidden).")
    x = values[indices]
    namespace = {"x": x, "np": np, "__builtins__": {}}
    try:
        result = eval(expr, namespace)  # noqa: S307 - restricted namespace, local trusted tool
    except Exception as exc:  # noqa: BLE001 - surface any eval error to the UI
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
