"""Selection state shared between the plot, selection tools and corrections."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np


class SelectionMode(Enum):
    POINT = "point"
    X_RANGE = "x_range"
    Y_RANGE = "y_range"
    XY_RECT = "xy_rect"


@dataclass
class SelectionState:
    mode: SelectionMode = SelectionMode.X_RANGE
    mask: Optional[np.ndarray] = None
    x_range: Optional[tuple[float, float]] = None
    y_range: Optional[tuple[float, float]] = None
    point_index: Optional[int] = None

    @property
    def count(self) -> int:
        if self.mask is None:
            return 0
        return int(np.count_nonzero(self.mask))

    def clear(self) -> None:
        self.mask = None
        self.x_range = None
        self.y_range = None
        self.point_index = None

    def set_mask(self, mask: np.ndarray) -> None:
        self.mask = mask
