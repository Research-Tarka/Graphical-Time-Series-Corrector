import numpy as np

from .base import CorrectionContext, CorrectionResult, CorrectionOperation, register_correction
from . import ops


@register_correction
class DeleteCorrection(CorrectionOperation):
    id = "delete"
    label = "Delete"
    needs_selection = True
    param_schema = []

    def apply(self, ctx: CorrectionContext) -> CorrectionResult:
        idx = np.where(ctx.selection_mask)[0]
        return CorrectionResult(idx, ops.op_delete(idx))
