"""Build interactive Plotly charts from a DataFrame.

CHARTS is the registry of chart types. To add a chart, write one builder function and add one
entry to CHARTS and BUILDERS; the Visualize page picks it up automatically.
"""

import math
import re
from dataclasses import dataclass, field

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core import config, profile

AGGREGATIONS = ["sum", "mean", "median", "count"]
OTHER = "Other"
MISSING_LABEL = "(missing)"

LABEL_KINDS = (profile.CATEGORICAL, profile.TEXT)
ORDERED_KINDS = (profile.DATETIME, profile.NUMERIC)


class ChartError(ValueError):
    """Raised when a chart cannot be drawn from the chosen data."""


@dataclass(frozen=True)
class ChartType:
    """What a chart needs, which tells the Visualize page which controls to show."""

    description: str
    x: tuple[str, ...] = ()
    y: tuple[str, ...] = ()
    x_optional: bool = False
    color: bool = False
    aggregates: bool = False
    stacks: bool = False
    bins: bool = False


@dataclass(frozen=True)
class ChartResult:
    figure: go.Figure
    data: pd.DataFrame  # the numbers behind the chart, shown as a table for readers
    notes: list[str] = field(default_factory=list)  # anything changed to make the chart readable


@dataclass(frozen=True)
class Request:
    """Everything a builder function needs to know."""

    df: pd.DataFrame
    x: str | None
    y: str | None
    color: str | None
    agg: str
    stacked: bool
    bins: int | None
    theme: dict


CHARTS = {
    "Bar": ChartType(
        "Compare a number across categories.",
        x=LABEL_KINDS + ORDERED_KINDS,
        y=(profile.NUMERIC,),
        color=True,
        aggregates=True,
        stacks=True,
    ),
    "Line": ChartType(
        "Show how a number changes over time or another order.",
        x=ORDERED_KINDS + LABEL_KINDS,
        y=(profile.NUMERIC,),
        color=True,
        aggregates=True,
    ),
    "Area": ChartType(
        "Show how a total and its parts change over time.",
        x=ORDERED_KINDS + LABEL_KINDS,
        y=(profile.NUMERIC,),
        color=True,
        aggregates=True,
    ),
    "Pie": ChartType(
        "Show how a whole splits into a few parts.",
        x=LABEL_KINDS,
        y=(profile.NUMERIC,),
    ),
    "Scatter": ChartType(
        "See whether two numbers move together.",
        x=(profile.NUMERIC, profile.DATETIME),
        y=(profile.NUMERIC,),
        color=True,
    ),
    "Histogram": ChartType(
        "See how the values of one column are spread out.",
        x=(profile.NUMERIC, profile.DATETIME, profile.CATEGORICAL),
        bins=True,
    ),
    "Box plot": ChartType(
        "Compare the spread of a number across groups and spot outliers.",
        x=(profile.CATEGORICAL,),
        y=(profile.NUMERIC,),
        x_optional=True,
    ),
    "Correlation heatmap": ChartType(
        "See which numeric columns move together (-1 opposite, 0 unrelated, +1 together)."
    ),
}


def column_kinds(df: pd.DataFrame) -> dict[str, str]:
    """The detected type of every column."""
    return {column: profile.detect_type(df[column]) for column in df.columns}


def columns_of_kind(kinds: dict[str, str], allowed: tuple[str, ...]) -> list[str]:
    """Columns whose type is allowed, keeping the dataset's column order."""
    return [column for column, kind in kinds.items() if kind in allowed]


def has_repeats(df: pd.DataFrame, x: str, color: str | None = None) -> bool:
    """True when several rows share one x (and colour), so they must be combined to plot."""
    return bool(df.duplicated(subset=list(dict.fromkeys([x, color or x]))).any())


def _prepare(
    df: pd.DataFrame, columns: list[str], color: str | None = None
) -> tuple[pd.DataFrame, list[str]]:
    """Copy the needed columns, fix their types and drop rows the chart cannot plot."""
    keep = list(dict.fromkeys(columns + ([color] if color else [])))
    data = df[keep].copy()
    for column in columns:
        data[column] = profile.to_real_type(data[column])

    before = len(data)
    data = data.dropna(subset=columns)
    if data.empty:
        raise ChartError("No rows have values in all of the chosen columns.")
    notes = []
    if len(data) < before:
        notes.append(f"Left out {before - len(data)} row(s) with missing or unreadable values.")
    if color:
        data[color] = data[color].astype(object).where(data[color].notna(), MISSING_LABEL)
        data[color] = data[color].astype(str)
    return data, notes


def _fold_rare(
    data: pd.DataFrame, column: str, value: str | None, limit: int
) -> tuple[pd.DataFrame, list[str]]:
    """Keep the largest groups and combine the rest into one "Other" group, listed last."""
    grouped = data.groupby(column, observed=True)
    sizes = grouped[value].sum().abs() if value else grouped.size()
    if len(sizes) <= limit:
        return data, []
    keep = sizes.nlargest(limit - 1).index
    data = data.copy()
    data[column] = data[column].astype(str).where(data[column].isin(keep), OTHER)
    data = data.sort_values(column, key=lambda labels: labels == OTHER, kind="stable")
    return data, [f"Combined the {len(sizes) - len(keep)} smallest '{column}' groups into {OTHER}."]


def _aggregate(
    data: pd.DataFrame, keys: list[str], y: str, agg: str
) -> tuple[pd.DataFrame, str]:
    """Combine rows that share the same keys; returns the data and the name of the value column."""
    keys = list(dict.fromkeys(keys))
    if agg != "count" and not data.duplicated(subset=keys).any():
        return data[keys + [y]], y
    label = f"{agg.capitalize()} of {y}"
    combined = data.groupby(keys, sort=False, observed=True)[y].agg(agg).reset_index()
    return combined.rename(columns={y: label}), label


def _sort_if_ordered(data: pd.DataFrame, x: str) -> pd.DataFrame:
    """Put dates and numbers in order; labels keep the order they have in the data."""
    is_ordered = pd.api.types.is_numeric_dtype(data[x]) or pd.api.types.is_datetime64_any_dtype(
        data[x]
    )
    return data.sort_values(x, kind="stable") if is_ordered else data


def _color_map(values, theme: dict) -> dict[str, str]:
    """Give each group a fixed colour based on its name, so it never depends on its rank."""
    names = sorted(set(values) - {OTHER})
    colors = {name: theme["series"][i] for i, name in enumerate(names)}
    if OTHER in set(values):
        colors[OTHER] = theme["muted"]
    return colors


def _color_args(data: pd.DataFrame, color: str | None, theme: dict) -> dict:
    """Plotly Express arguments for colouring by a column, or for one single colour."""
    if not color:
        return {"color_discrete_sequence": theme["series"][:1]}
    return {"color": color, "color_discrete_map": _color_map(data[color], theme)}


def _title_for(label: str, x: str, color: str | None) -> str:
    return f"{label} by {x}" + (f" and {color}" if color and color != x else "")


def _series_chart(
    req: Request, draw, x_limit: int | None = None
) -> tuple[go.Figure, pd.DataFrame, list[str], str]:
    """Shared preparation for the charts that plot one combined value per x: bar, line, area."""
    data, notes = _prepare(req.df, [req.x, req.y], req.color)
    if x_limit and profile.detect_type(data[req.x]) in LABEL_KINDS:
        data, folded = _fold_rare(data, req.x, req.y, x_limit)
        notes += folded
    if req.color:
        data, folded = _fold_rare(data, req.color, req.y, config.MAX_SERIES)
        notes += folded
    data, label = _aggregate(data, [req.x] + ([req.color] if req.color else []), req.y, req.agg)
    data = _sort_if_ordered(data, req.x)
    return draw(data, label), data, notes, _title_for(label, req.x, req.color)


def _bar(req: Request):
    stacked = req.stacked and req.color and req.agg in ("sum", "count")

    def draw(data, label):
        fig = px.bar(data, x=req.x, y=label, **_color_args(data, req.color, req.theme))
        fig.update_traces(marker_line_color=req.theme["surface"], marker_line_width=2)
        fig.update_layout(
            barmode="relative" if stacked or not req.color else "group",
            bargap=0.2,
            barcornerradius=4,
        )
        return fig

    figure, data, notes, title = _series_chart(req, draw, x_limit=config.BAR_MAX_CATEGORIES)
    if req.stacked and req.color and not stacked:
        notes.append(f"Bars are side by side because a {req.agg} can't be stacked.")
    return figure, data, notes, title


def _label_line_ends(fig: go.Figure, data: pd.DataFrame, req: Request, label: str) -> None:
    """Name each line at its last point, so a reader doesn't rely on colour alone."""
    if not req.color or data[req.color].nunique() > config.LINE_LABEL_MAX_SERIES:
        return
    for name, rows in data.groupby(req.color, sort=False):
        last = rows.iloc[-1]
        fig.add_annotation(
            x=last[req.x],
            y=last[label],
            text=name,
            xanchor="left",
            xshift=6,
            showarrow=False,
            font={"color": req.theme["secondary"]},
        )
    fig.update_layout(margin_r=110)


def _line(req: Request):
    def draw(data, label):
        fig = px.line(
            data,
            x=req.x,
            y=label,
            markers=len(data) <= config.LINE_MARKER_MAX_POINTS,
            **_color_args(data, req.color, req.theme),
        )
        fig.update_traces(line_width=2, marker_size=8)
        fig.update_layout(hovermode="x unified")
        _label_line_ends(fig, data, req, label)
        return fig

    return _series_chart(req, draw)


def _area(req: Request):
    def draw(data, label):
        fig = px.area(data, x=req.x, y=label, **_color_args(data, req.color, req.theme))
        fig.update_traces(line_width=2)
        fig.update_layout(hovermode="x unified")
        return fig

    return _series_chart(req, draw)


def _pie(req: Request):
    data, notes = _prepare(req.df, [req.x, req.y])
    if (data[req.y] < 0).any():
        raise ChartError(f"A pie chart can't show negative values, and '{req.y}' has some.")
    data[req.x] = data[req.x].astype(str)
    data, folded = _fold_rare(data, req.x, req.y, config.PIE_MAX_SLICES)
    data, label = _aggregate(data, [req.x], req.y, "sum")
    if len(data) < 2 or data[label].sum() == 0:
        raise ChartError("A pie chart needs at least two parts with values above zero.")

    fig = px.pie(
        data,
        names=req.x,
        values=label,
        color=req.x,
        color_discrete_map=_color_map(data[req.x], req.theme),
    )
    fig.update_traces(
        textinfo="percent",
        sort=False,
        marker_line_color=req.theme["surface"],
        marker_line_width=2,
    )
    return fig, data, notes + folded, f"Share of {req.y} by {req.x}"


def _scatter(req: Request):
    data, notes = _prepare(req.df, [req.x, req.y], req.color)
    args = _color_args(data, req.color, req.theme)
    facets = 0
    if req.color and data[req.color].nunique() > config.SCATTER_MAX_COLORS:
        data, folded = _fold_rare(data, req.color, None, config.MAX_SERIES)
        notes += folded
        facets = data[req.color].nunique()
        notes.append(f"Each '{req.color}' group has its own panel, so the points stay readable.")
        args = {
            "color_discrete_sequence": req.theme["series"][:1],
            "facet_col": req.color,
            "facet_col_wrap": config.SCATTER_MAX_COLORS,
            "category_orders": {req.color: sorted(data[req.color].unique())},
        }

    fig = px.scatter(data, x=req.x, y=req.y, **args)
    fig.update_traces(marker_size=10, marker_line_color=req.theme["surface"], marker_line_width=1)
    if facets:
        rows = math.ceil(facets / config.SCATTER_MAX_COLORS)
        fig.update_layout(height=120 + 280 * rows)
        fig.for_each_annotation(lambda note: note.update(text=note.text.split("=", 1)[-1]))
    return fig, data, notes, f"{req.y} vs {req.x}" + (f" by {req.color}" if req.color else "")


def _histogram(req: Request):
    data, notes = _prepare(req.df, [req.x])
    fig = px.histogram(
        data, x=req.x, nbins=req.bins, color_discrete_sequence=req.theme["series"][:1]
    )
    fig.update_traces(marker_line_color=req.theme["surface"], marker_line_width=1)
    fig.update_layout(bargap=0.05)
    # Small datasets get whole-number ticks: there is no such thing as half a row
    fig.update_yaxes(title_text="Number of rows", dtick=1 if len(data) <= 20 else None)
    return fig, data, notes, f"Distribution of {req.x}"


def _box(req: Request):
    columns = [req.y] + ([req.x] if req.x else [])
    data, notes = _prepare(req.df, columns)
    fig = px.box(
        data,
        x=req.x,
        y=req.y,
        points="outliers",
        color_discrete_sequence=req.theme["series"][:1],
    )
    title = f"{req.y} by {req.x}" if req.x else f"Distribution of {req.y}"
    return fig, data, notes, title


def _heatmap(req: Request):
    converted = req.df.apply(profile.to_real_type)
    numeric = converted.select_dtypes("number")
    varying = numeric.loc[:, numeric.nunique() > 1]
    if varying.shape[1] < 2:
        raise ChartError("A correlation heatmap needs at least two numeric columns that vary.")
    notes = []
    if varying.shape[1] < numeric.shape[1]:
        skipped = ", ".join(sorted(set(numeric.columns) - set(varying.columns)))
        notes.append(f"Left out {skipped}: a column with one repeated value has no correlation.")

    corr = varying.corr().round(2)
    theme = req.theme
    fig = px.imshow(
        corr,
        text_auto=True,
        zmin=-1,
        zmax=1,
        aspect="auto",
        labels={"x": "Column", "y": "Column", "color": "Correlation"},
        color_continuous_scale=[
            (0.0, theme["series"][7]),
            (0.5, theme["midpoint"]),
            (1.0, theme["series"][0]),
        ],
    )
    fig.update_traces(xgap=2, ygap=2)
    fig.update_xaxes(showline=False, title_text="")
    fig.update_yaxes(showgrid=False, showline=False, title_text="")
    data = corr.rename_axis("column").reset_index()
    return fig, data, notes, "Correlation between numeric columns"


BUILDERS = {
    "Bar": _bar,
    "Line": _line,
    "Area": _area,
    "Pie": _pie,
    "Scatter": _scatter,
    "Histogram": _histogram,
    "Box plot": _box,
    "Correlation heatmap": _heatmap,
}


def _style(fig: go.Figure, title: str, theme: dict) -> None:
    """Apply one look to every chart: quiet axes and grid, so the data stands out."""
    fig.update_layout(
        template="none",
        # The title sits at a fixed spot at the top, so the legend can be fitted below it
        title={
            "text": title,
            "xref": "paper",
            "x": 0,
            "yref": "container",
            "y": 1,
            "yanchor": "top",
            "pad": {"t": 20},
            "font": {"color": theme["ink"]},
        },
        paper_bgcolor=theme["surface"],
        plot_bgcolor=theme["surface"],
        font={"family": config.CHART_FONT, "color": theme["secondary"]},
        legend={"orientation": "h", "x": 0, "y": 1.02, "yanchor": "bottom", "title_text": ""},
        margin={"l": 60, "t": 90, "b": 60},
    )
    if not fig.layout.margin.r:
        fig.update_layout(margin_r=30)
    fig.update_xaxes(showgrid=False, linecolor=theme["baseline"], automargin=True)
    fig.update_yaxes(
        gridcolor=theme["grid"], zeroline=False, linecolor=theme["baseline"], automargin=True
    )


def build_chart(
    df: pd.DataFrame,
    chart: str,
    x: str | None = None,
    y: str | None = None,
    color: str | None = None,
    agg: str = "sum",
    stacked: bool = True,
    bins: int | None = None,
    title: str | None = None,
    dark: bool = False,
) -> ChartResult:
    """Build one chart. Raises ChartError when the chosen columns can't make that chart."""
    if chart not in BUILDERS:
        raise ChartError(f"Unknown chart type '{chart}'.")
    if agg not in AGGREGATIONS:
        raise ChartError(f"Unknown aggregation '{agg}'.")
    if x is not None and x == y:
        raise ChartError("Choose two different columns for X and Y.")

    theme = config.CHART_THEMES["dark" if dark else "light"]
    request = Request(df, x, y, color, agg, stacked, bins, theme)
    figure, data, notes, default_title = BUILDERS[chart](request)
    _style(figure, title or default_title, theme)
    return ChartResult(figure, data, notes)


def plot_config(result: ChartResult) -> dict:
    """Plotly settings: the camera button saves a sharp PNG named after the chart."""
    slug = re.sub(r"[^a-z0-9]+", "-", result.figure.layout.title.text.lower()).strip("-")
    return {
        "displaylogo": False,
        "toImageButtonOptions": {"format": "png", "filename": slug or "chart", "scale": 2},
    }
