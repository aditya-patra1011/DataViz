"""What the Kotlin app calls. All the data work stays in core/; this only translates.

Every function returns a JSON string: {"ok": true, ...} on success, or {"ok": false, "error": ...}
when the user's data or choices are the problem. Real bugs still raise, so they aren't hidden.
"""

import functools
import json
from dataclasses import dataclass, field
from io import BytesIO

import pandas as pd

from core import charts, clean, ingest, profile

PREVIEW_ROWS = 50
TABLE_ROWS = 200
USER_ERRORS = (ingest.IngestError, clean.CleanError, charts.ChartError)


@dataclass
class Session:
    """The dataset the app is working on. Python stays running while the app is open."""

    df: pd.DataFrame | None = None
    original: pd.DataFrame | None = None
    source: str = ""
    log: list[str] = field(default_factory=list)


session = Session()


def _respond(function):
    @functools.wraps(function)
    def wrapper(*args):
        try:
            return json.dumps({"ok": True, **function(*args)})
        except USER_ERRORS as err:
            return json.dumps({"ok": False, "error": str(err)})

    return wrapper


def _table(df: pd.DataFrame, limit: int) -> dict:
    """Part of a DataFrame as plain text, ready to show in a table."""
    part = df.head(limit)
    text = part.astype(str).where(part.notna(), "")
    return {"columns": [str(c) for c in part.columns], "rows": text.values.tolist()}


def _snapshot(message: str = "") -> dict:
    """Everything the Data and Clean screens need to draw themselves."""
    df = session.df
    if df is None:
        return {"loaded": False, "message": message}

    report = profile.column_report(df)
    limits = {
        name: profile.outlier_bounds(df[name])
        for name in report.loc[report["outliers"] > 0, "column"]
    }
    return {
        "loaded": True,
        "message": message,
        "source": session.source,
        "summary": profile.dataset_summary(df),
        "report": json.loads(report.to_json(orient="records")),
        "preview": _table(df, PREVIEW_ROWS),
        "shown_rows": min(len(df), PREVIEW_ROWS),
        "limits": limits,
        "log": session.log,
        "missing_strategies": clean.MISSING_STRATEGIES,
        "outlier_methods": clean.OUTLIER_METHODS,
    }


def _set_dataset(df: pd.DataFrame, source: str) -> dict:
    session.df = session.original = df
    session.source = source
    session.log = []
    rows = "1 row" if len(df) == 1 else f"{len(df):,} rows"
    columns = "1 column" if df.shape[1] == 1 else f"{df.shape[1]} columns"
    return _snapshot(f"Loaded {rows} and {columns} from {source}.")


@_respond
def snapshot() -> dict:
    return _snapshot()


@_respond
def load_file(content, filename: str, source: str) -> dict:
    return _set_dataset(ingest.read_file(BytesIO(bytes(content)), filename), source)


@_respond
def load_text(text: str) -> dict:
    return _set_dataset(ingest.parse_text(text), "pasted data")


@_respond
def load_table(table_json: str) -> dict:
    table = json.loads(table_json)
    return _set_dataset(ingest.from_table(table["columns"], table["rows"]), "typed data")


def _run_fix(action: str, column: str | None, choice: str | None, value: str | None):
    df = session.df
    if action == "convert":
        return clean.convert_types(df)
    if action == "duplicates":
        return clean.drop_duplicates(df)
    if action == "missing":
        return clean.fill_missing(df, column, choice, value)
    if action == "outliers":
        return clean.handle_outliers(df, column, choice)
    if action == "drop":
        return clean.drop_column(df, column)
    raise clean.CleanError(f"Unknown fix '{action}'.")


@_respond
def fix(action: str, column: str | None, choice: str | None, value: str | None) -> dict:
    session.df, message = _run_fix(action, column, choice, value)
    session.log = [*session.log, message]
    return _snapshot(message)


@_respond
def reset() -> dict:
    session.df = session.original
    session.log = []
    return _snapshot("Restored the original data.")


@_respond
def chart_options(chart: str, x: str | None, color: str | None) -> dict:
    """Which columns and controls suit this chart for the current dataset."""
    df = session.df
    spec = charts.CHARTS[chart]
    kinds = charts.column_kinds(df)
    valid_x = x in df.columns
    x_options = charts.columns_of_kind(kinds, spec.x)
    y_options = charts.columns_of_kind(kinds, spec.y)
    return {
        "charts": list(charts.CHARTS),
        "description": spec.description,
        "x": x_options,
        "x_optional": spec.x_optional,
        "y": y_options,
        "usable": not (spec.x and not spec.x_optional and not x_options)
        and not (spec.y and not y_options),
        "color": charts.columns_of_kind(kinds, (profile.CATEGORICAL,)) if spec.color else [],
        "aggregations": charts.AGGREGATIONS,
        "repeats": spec.aggregates and valid_x and charts.has_repeats(df, x, color),
        "stacks": spec.stacks and color is not None,
        "bins": spec.bins and valid_x and kinds[x] != profile.CATEGORICAL,
    }


@_respond
def draw(
    chart: str,
    x: str | None,
    y: str | None,
    color: str | None,
    agg: str,
    stacked: bool,
    bins: int | None,
    title: str | None,
    dark: bool,
) -> dict:
    result = charts.build_chart(
        session.df,
        chart,
        x=x,
        y=y,
        color=color,
        agg=agg,
        stacked=stacked,
        bins=bins,
        title=title or None,
        dark=dark,
    )
    return {
        "figure": result.figure.to_json(),
        "notes": result.notes,
        "data": _table(result.data, TABLE_ROWS),
    }
