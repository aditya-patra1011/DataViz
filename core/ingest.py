"""Load data from files, pasted text and the manual-entry table into pandas DataFrames."""

from io import StringIO
from pathlib import Path

import pandas as pd

from core import config


class IngestError(ValueError):
    """Raised when input cannot be turned into a usable DataFrame."""


def get_extension(filename: str) -> str:
    """Return the file extension in lowercase without the dot ("Sales.CSV" -> "csv")."""
    return Path(filename).suffix.lower().lstrip(".")


def clean_column_names(columns) -> list[str]:
    """Strip spaces, name blank or 'Unnamed' columns, and make every name unique."""
    names = []
    for i, col in enumerate(columns, start=1):
        name = str(col).strip()
        if not name or name.startswith("Unnamed:"):
            name = f"column_{i}"
        base, n = name, 2
        while name in names:
            name = f"{base}_{n}"
            n += 1
        names.append(name)
    return names


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Check a freshly loaded DataFrame is usable and tidy up its column names."""
    if df.empty:
        raise IngestError("The data is empty.")
    if len(df) > config.MAX_ROWS:
        raise IngestError(f"The data has {len(df):,} rows; the limit is {config.MAX_ROWS:,}.")
    df = df.copy()
    df.columns = clean_column_names(df.columns)
    return df


def _read_csv(file) -> pd.DataFrame:
    """Read CSV as UTF-8, falling back to Latin-1 for files saved by older Excel versions."""
    try:
        return pd.read_csv(file)
    except UnicodeDecodeError:
        if hasattr(file, "seek"):
            file.seek(0)
        return pd.read_csv(file, encoding="latin-1")


def read_file(file, filename: str) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame.

    `file` can be a path or a file-like object (such as Streamlit's UploadedFile).
    """
    ext = get_extension(filename)
    if ext not in config.ALLOWED_FILE_TYPES:
        allowed = ", ".join(config.ALLOWED_FILE_TYPES)
        raise IngestError(f"Unsupported file type '.{ext}'. Allowed: {allowed}")

    try:
        df = _read_csv(file) if ext == "csv" else pd.read_excel(file)
    except Exception as exc:
        raise IngestError(f"Could not read '{filename}': {exc}") from exc
    return validate(df)


def parse_text(text: str) -> pd.DataFrame:
    """Parse text pasted from a spreadsheet (tab-separated) or CSV text (comma-separated)."""
    text = text.strip()
    if not text:
        raise IngestError("Nothing was pasted.")

    first_line = text.splitlines()[0]
    sep = "\t" if "\t" in first_line else ","
    try:
        df = pd.read_csv(StringIO(text), sep=sep)
    except Exception as exc:
        raise IngestError(f"Could not parse the pasted data: {exc}") from exc
    return validate(df)


def parse_column_names(text: str) -> list[str]:
    """Turn "Label, Value" into ["Label", "Value"], skipping blanks and fixing duplicates."""
    names = [part.strip() for part in text.split(",") if part.strip()]
    if not names:
        raise IngestError("Enter at least one column name.")
    return clean_column_names(names)


def empty_table(columns: list[str], rows: int = 5) -> pd.DataFrame:
    """Blank table for manual entry: the first column holds labels, the rest hold numbers."""
    data = {columns[0]: [""] * rows}
    for col in columns[1:]:
        data[col] = [float("nan")] * rows
    return pd.DataFrame(data)


def from_editor(df: pd.DataFrame) -> pd.DataFrame:
    """Turn the manual-entry table into a dataset, dropping rows the user left blank."""
    df = df.replace("", pd.NA).dropna(how="all").reset_index(drop=True)
    return validate(df)


def list_samples() -> list[str]:
    """Names of the sample CSV files shipped with the app."""
    return sorted(path.name for path in config.SAMPLES_DIR.glob("*.csv"))


def load_sample(name: str) -> pd.DataFrame:
    """Load one of the sample datasets by file name."""
    return read_file(config.SAMPLES_DIR / name, name)
