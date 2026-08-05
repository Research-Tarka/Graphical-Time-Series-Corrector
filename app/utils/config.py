"""App-wide constants."""

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = APP_DIR.parent
LOG_DIR = APP_DIR / "logs"

# Plot colors
RAW_COLOR = (150, 150, 150)
CORRECTED_COLOR = (31, 119, 180)
SELECTION_COLOR = (255, 99, 71)
SPIKE_COLOR = (220, 20, 60)
FREEZE_COLOR = (255, 165, 0)

# Default detection parameters
DEFAULT_SPIKE_WINDOW = 24
DEFAULT_SPIKE_Z = 4.0
DEFAULT_FREEZE_RUN = 6
DEFAULT_FREEZE_TOL = 0.0

# Cache: max number of variables kept in memory per session
MAX_CACHED_VARIABLES = 12
