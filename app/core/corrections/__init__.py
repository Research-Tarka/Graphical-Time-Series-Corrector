"""Correction operations registry.

Importing this package registers every built-in correction operation in
``REGISTRY`` (see :mod:`app.core.corrections.base`). To add a new correction
type, create a new module in this package, register a class with
``@register_correction``, then import that module below.
"""

from .base import REGISTRY, DETECTION_REGISTRY, CorrectionContext, CorrectionResult, ParamSpec

from . import delete  # noqa: F401
from . import replace  # noqa: F401
from . import offset_scale  # noqa: F401
from . import expression  # noqa: F401
from . import threshold  # noqa: F401
from . import detection  # noqa: F401

__all__ = [
    "REGISTRY",
    "DETECTION_REGISTRY",
    "CorrectionContext",
    "CorrectionResult",
    "ParamSpec",
]
