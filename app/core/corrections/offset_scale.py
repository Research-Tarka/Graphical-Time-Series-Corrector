import numpy as np

from .base import CorrectionContext, CorrectionResult, CorrectionOperation, ParamSpec, register_correction
from . import ops


@register_correction
class OffsetCorrection(CorrectionOperation):
    id = "offset"
    label = "Offset (+/-)"
    needs_selection = True
    param_schema = [
        ParamSpec("amount", "float", "Value to add", default=0.0),
    ]

    def apply(self, ctx: CorrectionContext) -> CorrectionResult:
        idx = np.where(ctx.selection_mask)[0]
        return CorrectionResult(idx, ops.op_offset(ctx.values, idx, ctx.params["amount"]))


@register_correction
class MultiplyCorrection(CorrectionOperation):
    id = "multiply"
    label = "Multiply"
    needs_selection = True
    param_schema = [
        ParamSpec("factor", "float", "Multiplication factor", default=1.0),
    ]

    def apply(self, ctx: CorrectionContext) -> CorrectionResult:
        idx = np.where(ctx.selection_mask)[0]
        return CorrectionResult(idx, ops.op_multiply(ctx.values, idx, ctx.params["factor"]))
