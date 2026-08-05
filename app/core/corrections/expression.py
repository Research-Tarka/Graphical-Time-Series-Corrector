import numpy as np

from .base import CorrectionContext, CorrectionResult, CorrectionOperation, ParamSpec, register_correction
from . import ops


@register_correction
class CustomExpressionCorrection(CorrectionOperation):
    id = "expression"
    label = "Custom expression"
    needs_selection = True
    param_schema = [
        ParamSpec("expr", "expr", "Expression (x = selected value(s))", default="x"),
    ]

    def apply(self, ctx: CorrectionContext) -> CorrectionResult:
        idx = np.where(ctx.selection_mask)[0]
        return CorrectionResult(idx, ops.op_expression(ctx.values, idx, ctx.params["expr"]))
