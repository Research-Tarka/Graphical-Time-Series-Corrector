"""Spike and freeze (stuck-value) detectors.

These are registered like corrections (declarative ``param_schema`` for the
UI form) but return :class:`DetectionResult` (candidate indices + scores)
rather than new values. The UI highlights the candidates and lets the user
turn a subset into a normal selection, which then flows through the regular
correction pipeline.
"""

from __future__ import annotations

import numpy as np

from .base import CorrectionContext, DetectionResult, DetectionOperation, ParamSpec, register_detection


def find_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return (start, end) inclusive index pairs for contiguous True runs."""

    if mask.size == 0:
        return []
    padded = np.concatenate(([False], mask, [False])).astype(np.int8)
    diff = np.diff(padded)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0] - 1
    return list(zip(starts.tolist(), ends.tolist()))


@register_detection
class SpikeDetection(DetectionOperation):
    id = "spike"
    label = "Detect spikes"
    param_schema = [
        ParamSpec("window", "int", "Sliding window (points)", default=24),
        ParamSpec("z_thresh", "float", "Threshold (z-score)", default=4.0),
    ]

    def apply(self, ctx: CorrectionContext) -> DetectionResult:
        values = ctx.values
        window = max(int(ctx.params.get("window", 24)), 2)
        z_thresh = float(ctx.params.get("z_thresh", 4.0))

        n = values.size
        if n < 3:
            return DetectionResult(np.array([], dtype=int), np.array([]), "spike")

        diff = np.diff(values)
        half = max(window // 2, 1)
        padded = np.pad(diff, (half, half), mode="edge")
        windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * half + 1)

        with np.errstate(all="ignore"):
            med = np.nanmedian(windows, axis=1)
            mad = np.nanmedian(np.abs(windows - med[:, None]), axis=1)
            z = np.abs(diff - med) / (mad * 1.4826 + 1e-9)
        z = np.nan_to_num(z, nan=0.0, posinf=0.0, neginf=0.0)

        flagged = np.where(z > z_thresh)[0]
        # diff[i] = values[i+1] - values[i] -> the spike is the *later* point
        idx = np.unique(flagged + 1)
        idx = idx[idx < n]
        scores = z[idx - 1]
        return DetectionResult(idx, scores, "spike")


@register_detection
class FreezeDetection(DetectionOperation):
    id = "freeze"
    label = "Detect frozen (stuck) values"
    param_schema = [
        ParamSpec("min_run_length", "int", "Minimum number of identical points", default=6),
        ParamSpec("tolerance", "float", "Tolerance (max gap between values)", default=0.0),
    ]

    def apply(self, ctx: CorrectionContext) -> DetectionResult:
        values = ctx.values
        min_run_length = max(int(ctx.params.get("min_run_length", 6)), 2)
        tol = float(ctx.params.get("tolerance", 0.0))

        n = values.size
        if n < min_run_length:
            return DetectionResult(np.array([], dtype=int), np.array([]), "freeze")

        valid = ~np.isnan(values)
        same_pairs = (np.abs(np.diff(values)) <= tol) & valid[:-1] & valid[1:]

        indices_list = []
        scores_list = []
        for start, end in find_runs(same_pairs):
            run_points = end - start + 2  # number of identical consecutive values
            if run_points >= min_run_length:
                pts = np.arange(start, end + 2)
                indices_list.append(pts)
                scores_list.append(np.full(pts.shape, run_points, dtype=np.float64))

        if indices_list:
            idx = np.concatenate(indices_list)
            scores = np.concatenate(scores_list)
        else:
            idx = np.array([], dtype=int)
            scores = np.array([])
        return DetectionResult(idx, scores, "freeze")
