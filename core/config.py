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
