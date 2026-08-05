import numpy as np

from .base import CorrectionContext, CorrectionResult, CorrectionOperation, ParamSpec, register_correction
from . import ops


@register_correction
class ThresholdCorrection(CorrectionOperation):
    """Flag values inside/outside a [min, max] range, then act on them.

    Unlike the other corrections, this one does not need a selection: it
    scans the whole (currently loaded) variable.
    """

    id = "threshold"
    label = "Threshold / min-max range"
    needs_selection = False
    param_schema = [
        ParamSpec("min", "optional_float", "Minimum", default=None),
        ParamSpec("max", "optional_float", "Maximum", default=None),
        ParamSpec(
            "mode",
            "enum",
            "Apply to values",
            default="outside",
            choices=[
                ("outside", "Outside the range"),
                ("inside", "Inside the range"),
            ],
        ),
        ParamSpec(
            "action",
            "enum",
            "Action",
            default="delete",
            choices=ops.ACTION_CHOICES,
        ),
        ParamSpec("replace_value", "float", "Replacement value", default=0.0,
                  depends_on=("action", ("replace",))),
        ParamSpec("offset_amount", "float", "Value to add", default=0.0,
                  depends_on=("action", ("offset",))),
        ParamSpec("factor", "float", "Multiplication factor", default=1.0,
                  depends_on=("action", ("multiply",))),
        ParamSpec("expr", "expr", "Expression (x = value(s))", default="x",
                  depends_on=("action", ("expression",))),
    ]

    def apply(self, ctx: CorrectionContext) -> CorrectionResult:
        values = ctx.values
        vmin = ctx.params.get("min")
        vmax = ctx.params.get("max")
        mode = ctx.params.get("mode", "outside")
        action = ctx.params.get("action", "delete")

        valid = ~np.isnan(values)
        if vmin is not None and vmax is not None:
            in_range = (values >= vmin) & (values <= vmax)
        elif vmin is not None:
            in_range = values >= vmin
        elif vmax is not None:
            in_range = values <= vmax
        else:
            in_range = np.ones(values.shape, dtype=bool)

        if mode == "inside":
            mask = valid & in_range
        else:
            mask = valid & ~in_range

        idx = np.where(mask)[0]
        new_values = ops.apply_action(values, idx, action, ctx.params)
        return CorrectionResult(idx, new_values)
