"""Fix common data problems.

Every function takes a DataFrame and returns (new DataFrame, message describing the change).
The input DataFrame is never modified, so the original data can always be restored.
"""

import pandas as pd

from core import profile

MISSING_STRATEGIES = ["drop rows", "mean", "median", "most common", "fixed value"]
OUTLIER_METHODS = ["remove rows", "cap at limits"]


class CleanError(ValueError):
    """Raised when a cleaning step cannot be applied."""


def _check_column(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        raise CleanError(f"Column '{column}' does not exist.")


def convert_types(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Turn text columns that hold numbers or dates into real numeric/datetime columns."""
    df = df.copy()
    changes = []
    for column in df.columns:
        kind = profile.detect_type(df[column])
        if not profile.needs_conversion(df[column], kind):
            continue
        before = int(df[column].notna().sum())
        convert = profile.to_number if kind == profile.NUMERIC else profile.to_datetime
        df[column] = convert(df[column])
        lost = before - int(df[column].notna().sum())
        note = f" ({lost} unreadable value(s) became missing)" if lost else ""
        changes.append(f"'{column}' to {kind}{note}")

    if not changes:
        raise CleanError("No columns need converting.")
    return df, "Converted " + "; ".join(changes) + "."


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Remove rows that are exact copies of an earlier row."""
    count = int(df.duplicated().sum())
    if count == 0:
        raise CleanError("There are no duplicate rows.")
    return df.drop_duplicates().reset_index(drop=True), f"Removed {count} duplicate row(s)."


def fill_missing(
    df: pd.DataFrame, column: str, strategy: str, value: str | None = None
) -> tuple[pd.DataFrame, str]:
    """Drop or fill the missing values in one column."""
    _check_column(df, column)
    series = df[column]
    missing = int(series.isna().sum())
    if missing == 0:
        raise CleanError(f"'{column}' has no missing values.")
    is_number = pd.api.types.is_numeric_dtype(series)

    if strategy == "drop rows":
        df = df.dropna(subset=[column]).reset_index(drop=True)
        return df, f"Dropped {missing} row(s) with missing '{column}'."

    if strategy in ("mean", "median", "most common") and series.notna().sum() == 0:
        raise CleanError(f"'{column}' has no values to calculate a {strategy} from.")

    if strategy in ("mean", "median"):
        if not is_number:
            raise CleanError(f"'{column}' is not numeric, so it has no {strategy}.")
        fill = series.mean() if strategy == "mean" else series.median()
        fill = round(float(fill), 2)
    elif strategy == "most common":
        fill = series.mode().iloc[0]
    elif strategy == "fixed value":
        if value is None or not value.strip():
            raise CleanError("Enter a value to fill with.")
        fill = value.strip()
        if is_number:
            try:
                fill = float(fill)
            except ValueError as exc:
                raise CleanError(f"'{column}' is numeric, so the value must be a number.") from exc
    else:
        raise CleanError(f"Unknown strategy '{strategy}'.")

    df = df.copy()
    df[column] = series.fillna(fill)
    return df, f"Filled {missing} missing '{column}' value(s) with the {strategy} ({fill})."


def handle_outliers(df: pd.DataFrame, column: str, method: str) -> tuple[pd.DataFrame, str]:
    """Remove outlier rows, or cap outliers at the normal range, for one numeric column."""
    _check_column(df, column)
    series = df[column]
    if not pd.api.types.is_numeric_dtype(series):
        raise CleanError(f"'{column}' is not numeric.")
    mask = profile.outlier_mask(series)
    count = int(mask.sum())
    if count == 0:
        raise CleanError(f"'{column}' has no outliers.")

    low, high = profile.outlier_bounds(series)
    limits = f"{low:.2f} to {high:.2f}"
    if method == "remove rows":
        df = df[~mask].reset_index(drop=True)
        return df, f"Removed {count} row(s) with outliers in '{column}' (outside {limits})."
    if method == "cap at limits":
        df = df.copy()
        df[column] = series.clip(low, high)
        return df, f"Capped {count} outlier(s) in '{column}' to {limits}."
    raise CleanError(f"Unknown method '{method}'.")


def drop_column(df: pd.DataFrame, column: str) -> tuple[pd.DataFrame, str]:
    """Remove one column."""
    _check_column(df, column)
    if df.shape[1] == 1:
        raise CleanError("You can't drop the only column.")
    return df.drop(columns=column), f"Dropped column '{column}'."
