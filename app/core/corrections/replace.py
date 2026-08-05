import numpy as np

from .base import CorrectionContext, CorrectionResult, CorrectionOperation, ParamSpec, register_correction
from . import ops


@register_correction
class ReplaceCorrection(CorrectionOperation):
    id = "replace"
    label = "Replace with a value"
    needs_selection = True
    param_schema = [
        ParamSpec("value", "float", "Replacement value", default=0.0),
    ]

    def apply(self, ctx: CorrectionContext) -> CorrectionResult:
        idx = np.where(ctx.selection_mask)[0]
        return CorrectionResult(idx, ops.op_replace(idx, ctx.params["value"]))
