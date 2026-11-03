"""Project-wide settings. Change values here instead of hard-coding them elsewhere."""

from pathlib import Path

# Folders
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SAMPLES_DIR = DATA_DIR / "samples"
DB_PATH = DATA_DIR / "app.db"

# App
APP_TITLE = "DataViz"
APP_ICON = "📊"

# Uploads
ALLOWED_FILE_TYPES = ["csv", "xlsx"]
MAX_ROWS = 100_000

# Data profiling
CATEGORICAL_MAX_UNIQUE = 20  # text columns with this many distinct values or fewer are categories
PARSE_THRESHOLD = 0.8  # share of text values that must parse to count as numbers or dates
IQR_MULTIPLIER = 1.5  # outliers lie this many IQRs below Q1 or above Q3

# Charts
BAR_MAX_CATEGORIES = 30  # beyond this, the smallest categories fold into "Other"
PIE_MAX_SLICES = 6
MAX_SERIES = 8  # the most colours a chart may use to tell groups apart
SCATTER_MAX_COLORS = 3  # scattered points overlap, so more groups get one panel each
LINE_LABEL_MAX_SERIES = 4  # up to this many lines are labelled directly at their last point
LINE_MARKER_MAX_POINTS = 40  # up to this many points, lines also show a dot on each point
CHART_FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
CHART_THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "ink": "#0b0b0b",
        "secondary": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "baseline": "#c3c2b7",
        "midpoint": "#f0efec",
        "series": [
            "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
            "#e87ba4", "#008300", "#6250d6", "#e34948",
        ],
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#f0efec",
        "secondary": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "baseline": "#383835",
        "midpoint": "#383835",
        "series": [
            "#3987e5", "#d95926", "#199e70", "#c98500",
            "#d55181", "#008300", "#9085e9", "#e66767",
        ],
    },
}
