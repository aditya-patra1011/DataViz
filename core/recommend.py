"""Suggest charts that suit a dataset, based on the types of its columns."""

from dataclasses import asdict, dataclass

import pandas as pd

from core import charts, config, profile, stats

# Below this, two columns are too loosely related for a scatter plot to be the best start
SUGGEST_MIN_CORRELATION = 0.3


@dataclass(frozen=True)
class Suggestion:
    chart: str
    reason: str
    x: str | None = None
    y: str | None = None
    color: str | None = None
    agg: str = "mean"

    def to_dict(self) -> dict:
        return asdict(self)


def _fits_a_pie(df: pd.DataFrame, group: str, value: str) -> bool:
    numbers = profile.to_real_type(df[value])
    return df[group].nunique() <= config.PIE_MAX_SLICES and (numbers.dropna() >= 0).all()


def suggest(df: pd.DataFrame) -> list[Suggestion]:
    """The charts most likely to be useful for this dataset, best first."""
    kinds = charts.column_kinds(df)
    numeric = charts.columns_of_kind(kinds, (profile.NUMERIC,))
    dates = charts.columns_of_kind(kinds, (profile.DATETIME,))
    groups = stats.grouping_columns(df)
    found = []

    if dates and numeric:
        reason = f"Shows how {numeric[0]} changes over {dates[0]}."
        color = groups[0] if groups else None
        found.append(Suggestion("Line", reason, dates[0], numeric[0], color))
    if groups and numeric:
        reason = f"Compares average {numeric[0]} across each {groups[0]}."
        found.append(Suggestion("Bar", reason, groups[0], numeric[0]))

    pair = stats.strongest_pair(stats.with_real_types(df))
    if pair and abs(pair[2]) >= SUGGEST_MIN_CORRELATION:
        first, second, value = pair
        reason = f"{first} and {second} are the closest related pair (correlation {value:.2f})."
        found.append(Suggestion("Scatter", reason, first, second))
    if len(numeric) >= 3:
        found.append(Suggestion("Correlation heatmap", "Shows how all the numeric columns relate."))
    if numeric:
        reason = f"Shows how the values of {numeric[0]} are spread out."
        found.append(Suggestion("Histogram", reason, numeric[0]))
    if groups and numeric and _fits_a_pie(df, groups[0], numeric[0]):
        reason = f"Shows each {groups[0]}'s share of the total {numeric[0]}."
        found.append(Suggestion("Pie", reason, groups[0], numeric[0], agg="sum"))

    return found[: config.MAX_SUGGESTIONS]
