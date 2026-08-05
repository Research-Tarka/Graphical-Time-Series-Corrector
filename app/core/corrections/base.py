"""Data contracts and registry for correction / detection operations.

A "correction" is any operation that takes the current values of a variable,
a selection mask, and a set of parameters, and returns new values for a set
of indices. Each correction is a small class registered with
``@register_correction`` and declares its parameters via ``param_schema`` so
the UI can build a form automatically.

A "detection" (spike / freeze) follows the same idea but returns a
:class:`DetectionResult` (candidate indices + scores) instead of new values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np


@dataclass
class ParamSpec:
    """Declarative description of one parameter / form field."""

    name: str
    type: str  # "float", "int", "optional_float", "enum", "str"
    label: str
    default: Any = None
    choices: Optional[list[tuple[str, str]]] = None  # (value, display label), for "enum"
    # (other_param_name, tuple of values for which this field is visible)
    depends_on: Optional[tuple[str, tuple[Any, ...]]] = None


@dataclass
class CorrectionContext:
    """Everything an operation needs to compute its result."""

    values: np.ndarray  # float64, current ("corrected") values of the variable
    timestamps: np.ndarray  # datetime64[ns], same length as values
    selection_mask: Optional[np.ndarray]  # bool array, same length, or None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrectionResult:
    """Indices that changed and their new values."""

    indices: np.ndarray  # int array
    new_values: np.ndarray  # float64 array, same length as indices


@dataclass
class DetectionResult:
    """Candidate indices found by a spike/freeze detector, with a score each."""

    indices: np.ndarray
    scores: np.ndarray
    kind: str  # "spike" or "freeze"


class CorrectionOperation:
    """Base class for correction operations. Subclass + register."""

    id: str = ""
    label: str = ""
    needs_selection: bool = True
    param_schema: list[ParamSpec] = []

    def apply(self, ctx: CorrectionContext) -> CorrectionResult:
        raise NotImplementedError


class DetectionOperation:
    """Base class for spike/freeze detection operations."""

    id: str = ""
    label: str = ""
    param_schema: list[ParamSpec] = []

    def apply(self, ctx: CorrectionContext) -> DetectionResult:
        raise NotImplementedError


REGISTRY: dict[str, CorrectionOperation] = {}
DETECTION_REGISTRY: dict[str, DetectionOperation] = {}


def register_correction(cls):
    """Class decorator: instantiate and register a CorrectionOperation."""

    instance = cls()
    REGISTRY[instance.id] = instance
    return cls


def register_detection(cls):
    """Class decorator: instantiate and register a DetectionOperation."""

    instance = cls()
    DETECTION_REGISTRY[instance.id] = instance
    return cls
