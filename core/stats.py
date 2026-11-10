"""Summary statistics and plain-English findings about a dataset."""

import pandas as pd

from core import charts, config, profile

MIN_ROWS_FOR_CORRELATION = 5
MIN_PERIODS_FOR_TREND = 3
STRONG_CORRELATION = 0.5
MAX_QUALITY_NOTES = 3


def with_real_types(df: pd.DataFrame) -> pd.DataFrame:
    """A copy where numbers and dates stored as text have been converted."""
    return df.apply(profile.to_real_type)


def grouping_columns(df: pd.DataFrame) -> list[str]:
    """Categorical columns that split the rows into a few real groups, fewest groups first."""
    kinds = charts.column_kinds(df)
    columns = [
        column
        for column in charts.columns_of_kind(kinds, (profile.CATEGORICAL,))
        if 2 <= df[column].nunique() <= config.MAX_SERIES and df[column].nunique() < len(df)
    ]
    return sorted(columns, key=lambda column: df[column].nunique())


def strongest_pair(df: pd.DataFrame) -> tuple[str, str, float] | None:
    """The two numeric columns that move together most closely, with their correlation."""
    numeric = df.select_dtypes("number")
    varying = numeric.loc[:, numeric.nunique() > 1]
    if varying.shape[1] < 2 or len(varying.dropna()) < MIN_ROWS_FOR_CORRELATION:
        return None
    best = None
    columns = list(varying.columns)
    for i, first in enumerate(columns):
        for second in columns[i + 1 :]:
            value = varying[first].corr(varying[second])
            if pd.notna(value) and (best is None or abs(value) > abs(best[2])):
                best = (first, second, float(value))
    return best


def summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """Count, mean, median, spread and range of every numeric column."""
    numeric = with_real_types(df).select_dtypes("number")
    if numeric.empty:
        return pd.DataFrame(columns=["column", "count", "mean", "median", "std", "min", "max"])
    table = numeric.agg(["count", "mean", "median", "std", "min", "max"]).T
    return table.round(2).rename_axis("column").reset_index()


def _period(date: pd.Timestamp, monthly: bool) -> str:
    return date.strftime("%b %Y" if monthly else "%d %b %Y")


def _trend_finding(data: pd.DataFrame) -> list[str]:
    dates = data.select_dtypes("datetime").columns
    numeric = data.select_dtypes("number").columns
    if len(dates) == 0 or len(numeric) == 0:
        return []
    value = numeric[0]
    series = data.dropna(subset=[dates[0], value]).groupby(dates[0])[value].mean().sort_index()
    if len(series) < MIN_PERIODS_FOR_TREND:
        return []

    monthly = all(date.day == 1 for date in series.index)
    # Compare the first and last quarter of the period, so one unusual day can't decide the trend
    edge = max(1, len(series) // 4)
    start, end = series.iloc[:edge].mean(), series.iloc[-edge:].mean()
    span = f"{_period(series.index[0], monthly)} to {_period(series.index[-1], monthly)}"
    peak = f"{_period(series.idxmax(), monthly)} ({series.max():,.1f})"
    if start > 0:
        change = (end - start) / start * 100
        word = "rose" if change >= 0 else "fell"
        return [
            f"Average {value} {word} {abs(change):.0f}% over {span}, and peaked in {peak}."
        ]
    return [f"Average {value} peaked in {peak}, over the period {span}."]


def _group_finding(df: pd.DataFrame, data: pd.DataFrame) -> list[str]:
    groups = grouping_columns(df)
    numeric = data.select_dtypes("number").columns
    if not groups or len(numeric) == 0:
        return []
    value = numeric[0]
    means = data.dropna(subset=[groups[0], value]).groupby(groups[0])[value].mean()
    if len(means) < 2 or means.max() == means.min():
        return []
    top, bottom = means.idxmax(), means.idxmin()
    return [
        f"{top} has the highest average {value} ({means.max():,.1f}); "
        f"{bottom} has the lowest ({means.min():,.1f})."
    ]


def _correlation_finding(data: pd.DataFrame) -> list[str]:
    pair = strongest_pair(data)
    if pair is None or abs(pair[2]) < STRONG_CORRELATION:
        return []
    first, second, value = pair
    direction = "rises as the other rises" if value > 0 else "falls as the other rises"
    return [
        f"{first} and {second} are strongly related: one {direction} (correlation {value:.2f}). "
        "This doesn't prove that one causes the other."
    ]


def _quality_findings(df: pd.DataFrame) -> list[str]:
    report = profile.column_report(df)
    notes = []
    for row in report[report["missing"] > 0].itertuples():
        notes.append(f"{row.column} is missing {row.missing} of its values.")
    for row in report[report["outliers"] > 0].itertuples():
        word = "value" if row.outliers == 1 else "values"
        notes.append(f"{row.column} has {row.outliers} unusual {word}; see the Clean tab.")
    return notes[:MAX_QUALITY_NOTES]


def insights(df: pd.DataFrame) -> list[str]:
    """Short plain-English findings, the most useful first."""
    data = with_real_types(df)
    findings = [
        *_trend_finding(data),
        *_group_finding(df, data),
        *_correlation_finding(data),
        *_quality_findings(df),
    ]
    return findings or ["No clear patterns stood out in this dataset."]
