"""Describe a dataset: column types, missing values, duplicate rows and outliers."""

import pandas as pd

from core import config

NUMERIC = "numeric"
DATETIME = "datetime"
CATEGORICAL = "categorical"
TEXT = "text"

# Characters people often type inside numbers: thousands separators, currency, percent
NUMBER_NOISE = r"[,\s$€£₹%]"


def to_number(series: pd.Series) -> pd.Series:
    """Convert text like "1,200" or "$5" to numbers; anything unreadable becomes NaN."""
    cleaned = series.astype("string").str.replace(NUMBER_NOISE, "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").astype("float64")


def to_datetime(series: pd.Series) -> pd.Series:
    """Convert date-like text to datetimes; anything unreadable becomes NaT."""
    return pd.to_datetime(series.astype("string"), errors="coerce", format="mixed")


def detect_type(series: pd.Series) -> str:
    """Classify a column as numeric, datetime, categorical or text."""
    values = series.dropna()
    if values.empty:
        return TEXT
    if pd.api.types.is_bool_dtype(values):
        return CATEGORICAL
    if pd.api.types.is_numeric_dtype(values):
        return NUMERIC
    if pd.api.types.is_datetime64_any_dtype(values):
        return DATETIME

    text = values.astype("string").str.strip()
    if to_number(text).notna().mean() >= config.PARSE_THRESHOLD:
        return NUMERIC
    # Only try dates when every value has a digit, so words like "Jan" or "May" stay text
    has_digits = text.str.contains(r"\d").all()
    if has_digits and to_datetime(text).notna().mean() >= config.PARSE_THRESHOLD:
        return DATETIME

    unique = text.nunique()
    if unique <= config.CATEGORICAL_MAX_UNIQUE or unique / len(text) <= 0.5:
        return CATEGORICAL
    return TEXT


def needs_conversion(series: pd.Series, kind: str) -> bool:
    """True when a column holds numbers or dates but is stored as text."""
    if kind == NUMERIC:
        return not pd.api.types.is_numeric_dtype(series)
    if kind == DATETIME:
        return not pd.api.types.is_datetime64_any_dtype(series)
    return False


def outlier_bounds(series: pd.Series) -> tuple[float, float]:
    """Lower and upper limits of normal values, using the IQR rule."""
    q1, q3 = series.quantile([0.25, 0.75])
    spread = config.IQR_MULTIPLIER * (q3 - q1)
    return float(q1 - spread), float(q3 + spread)


def outlier_mask(series: pd.Series) -> pd.Series:
    """True for each value outside the outlier bounds (missing values count as False)."""
    low, high = outlier_bounds(series)
    return (series < low) | (series > high)


def column_report(df: pd.DataFrame) -> pd.DataFrame:
    """One row per column: detected type, missing values, unique values and outliers."""
    rows = []
    for name in df.columns:
        series = df[name]
        kind = detect_type(series)
        missing = int(series.isna().sum())
        is_number = kind == NUMERIC and pd.api.types.is_numeric_dtype(series)
        rows.append(
            {
                "column": name,
                "type": kind,
                "stored as": str(series.dtype),
                "missing": missing,
                "missing %": round(100 * missing / len(df), 1) if len(df) else 0.0,
                "unique": int(series.nunique()),
                "outliers": int(outlier_mask(series).sum()) if is_number else 0,
                "needs conversion": needs_conversion(series, kind),
            }
        )
    return pd.DataFrame(rows)


def dataset_summary(df: pd.DataFrame) -> dict[str, int]:
    """Headline numbers for the whole dataset."""
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "missing cells": int(df.isna().sum().sum()),
        "duplicate rows": int(df.duplicated().sum()),
    }
